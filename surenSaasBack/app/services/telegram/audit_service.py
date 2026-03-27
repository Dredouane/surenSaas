"""
Service: Audit

Audit de toutes les interactions avec les bots Telegram.
Permet le monitoring et le debugging.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class TelegramAuditService:
    """Service d'audit pour les interactions Telegram."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def create_log(
        self,
        bot_id: str,
        telegram_user_id: int,
        interaction_type: str,
        payload: Dict[str, Any],
        org_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée une entrée d'audit pour une interaction.
        
        Args:
            bot_id: UUID du bot
            telegram_user_id: ID Telegram de l'utilisateur
            interaction_type: Type d'interaction (enum)
            payload: Données brutes de l'interaction
            org_id: UUID de l'org (optionnel, récupéré automatiquement si non fourni)
            
        Returns:
            L'entrée d'audit créée
        """
        # Récupérer org_id si non fourni
        if not org_id:
            bot = self.supabase.table('telegram_bots') \
                .select('org_id') \
                .eq('id', bot_id) \
                .single() \
                .execute()
            org_id = bot.data['org_id'] if bot.data else None
        
        audit_data = {
            'id': str(uuid.uuid4()),
            'org_id': org_id,
            'bot_id': bot_id,
            'telegram_user_id': telegram_user_id,
            'interaction_type': interaction_type,
            'status': 'pending',
            'payload': payload,
            'result': {},
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = self.supabase.table('telegram_audit').insert(audit_data).execute()
        return result.data[0] if result.data else audit_data
    
    async def update_log(
        self,
        audit_log_id: str,
        status: Optional[str] = None,
        result_data: Optional[Dict] = None,
        workflow_name: Optional[str] = None,
        workflow_step: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> bool:
        """
        Met à jour une entrée d'audit existante.
        
        Returns:
            True si mise à jour réussie
        """
        update_data = {'updated_at': datetime.utcnow().isoformat()}
        
        if status:
            update_data['status'] = status
        if result_data:
            update_data['result'] = result_data
        if workflow_name:
            update_data['workflow_name'] = workflow_name
        if workflow_step:
            update_data['workflow_step'] = workflow_step
        if workflow_id:
            update_data['workflow_id'] = workflow_id
        
        update_result = self.supabase.table('telegram_audit') \
            .update(update_data) \
            .eq('id', audit_log_id) \
            .execute()
        
        return len(update_result.data) > 0 if update_result.data else False
    
    async def complete_log(
        self,
        audit_log_id: str,
        status: str,
        result_data: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Marque une entrée d'audit comme terminée.

        Args:
            audit_log_id: ID de l'audit
            status: 'completed', 'failed', ou 'cancelled'
            result_data: Résultat de l'interaction
            error: Message d'erreur si failed
        """
        update_data = {
            'status': status,
            'completed_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        if result_data:
            update_data['result'] = result_data
        if error:
            update_data['error_message'] = error

        complete_result = self.supabase.table('telegram_audit') \
            .update(update_data) \
            .eq('id', audit_log_id) \
            .execute()

        return len(complete_result.data) > 0 if complete_result.data else False
    
    async def log_error(
        self,
        audit_log_id: str,
        error_message: str,
        error_type: str = 'general'
    ) -> bool:
        """Log une erreur sur une entrée d'audit existante."""
        return await self.complete_log(
            audit_log_id=audit_log_id,
            status='failed',
            error=error_message
        )
    
    async def log_workflow_step(
        self,
        audit_log_id: str,
        workflow_name: str,
        step: str,
        step_data: Optional[Dict] = None
    ) -> bool:
        """Log une étape de workflow."""
        return await self.update_log(
            audit_log_id=audit_log_id,
            workflow_name=workflow_name,
            workflow_step=step,
            result_data=step_data
        )
    
    async def get_recent_interactions(
        self,
        org_id: str,
        bot_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Récupère les interactions récentes.
        
        Returns:
            Dict avec les logs et métadonnées
        """
        query = self.supabase.table('telegram_audit') \
            .select('*') \
            .eq('org_id', org_id) \
            .order('created_at', desc=True) \
            .limit(limit) \
            
        
        if bot_id:
            query = query.eq('bot_id', bot_id)
        if status:
            query = query.eq('status', status)
        
        result = query.execute()
        
        # Compter le total
        count_result = self.supabase.table('telegram_audit') \
            .select('*', count='exact') \
            .eq('org_id', org_id) \
            .execute()
        
        return {
            'logs': result.data or [],
            'total': count_result.count,
            'limit': limit,
            'offset': offset
        }
    
    async def get_failed_interactions(
        self,
        org_id: str,
        hours: int = 24,
        limit: int = 100
    ) -> list:
        """
        Récupère les interactions échouées récentes.
        
        Args:
            org_id: UUID de l'org
            hours: Nombre d'heures à regarder en arrière
            limit: Limite de résultats
            
        Returns:
            Liste des logs d'erreurs
        """
        result = self.supabase.table('telegram_audit') \
            .select('*') \
            .eq('org_id', org_id) \
            .eq('status', 'failed') \
            .gte('created_at', f'now() - interval \'{hours} hours\'') \
            .order('created_at', desc=True) \
            .limit(limit) \
            .execute()
        
        return result.data or []
    
    async def get_stats(
        self,
        org_id: str,
        bot_id: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Récupère les statistiques d'utilisation.
        
        Returns:
            Dict avec les stats
        """
        # Base query
        base_query = self.supabase.table('telegram_audit') \
            .select('*') \
            .eq('org_id', org_id) \
            .gte('created_at', f'now() - interval \'{days} days\'')
        
        if bot_id:
            base_query = base_query.eq('bot_id', bot_id)
        
        # Total interactions
        total_result = base_query.execute()
        total = len(total_result.data) if total_result.data else 0
        
        # Par status
        completed = len([l for l in (total_result.data or []) if l.get('status') == 'completed'])
        failed = len([l for l in (total_result.data or []) if l.get('status') == 'failed'])
        pending = len([l for l in (total_result.data or []) if l.get('status') == 'pending'])
        
        # Par type
        types = {}
        for log in (total_result.data or []):
            t = log.get('interaction_type', 'unknown')
            types[t] = types.get(t, 0) + 1
        
        return {
            'period_days': days,
            'total_interactions': total,
            'by_status': {
                'completed': completed,
                'failed': failed,
                'pending': pending
            },
            'by_type': types,
            'success_rate': (completed / total * 100) if total > 0 else 0
        }
