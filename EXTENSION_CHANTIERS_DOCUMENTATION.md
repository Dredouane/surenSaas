# 📋 Documentation: Extension Gestion des Chantiers

## 🎯 Vue d'ensemble

Cette documentation décrit l'extension du système de gestion des chantiers avec 3 nouvelles fonctionnalités principales, en mode prototypage front/backend Next.js avec données statiques.

### **Fonctionnalités ajoutées:**
1. **Réceptions chantiers** - Système de réunions client avec validation et tâches
2. **Tâches direction → conducteur** - Système de notifications push et assignation
3. **Pointages hommes/machines** - Affectation quotidienne avec notification matinale

### **État: Prototypage COMPLÉTÉ**
- ✅ Données statiques complètes
- ✅ Types TypeScript étendus
- ✅ 4/4 Composants frontend créés
- ✅ Design onglets modernisé
- 🔄 API routes mockées (prochaine itération)
- 🔄 Intégration Telegram bot (planifiée)

---

## 📊 Structure des données

### **Nouvelles entités**

#### **1. Réception (Reception)**
Représente une réunion avec le client pour discuter, valider, soulever des points à régler.

**Champs:**
- `id`, `chantierId`, `date`, `type` (livraison/validation/problème/suivi)
- `statut` (planifiée/en cours/terminée/annulée)
- `participants`, `ordreDuJour`, `décisions`, `pointsARegler`
- `documents` (URLs), `createdAt`, `updatedAt`

#### **2. Tâche Réception (TacheReception)**
Tâches spécifiques générées depuis une réception.

**Champs:**
- `id`, `receptionId`, `description`, `assigneeId`, `assigneeName`
- `echeance`, `statut`, `priorite`, `commentaires`

#### **3. Tâche Générique (Tache)**
Tâches de la direction vers les conducteurs, avec système de notifications.

**Champs:**
- `id`, `chantierId` (optionnel), `titre`, `description`, `type` (information/action/validation/rapport)
- `source` (direction/système/client), `createurId`, `createurNom`
- `assigneeId`, `assigneeNom`, `echeance`, `statut`, `priorite`
- `reponse` (du conducteur), `documents`, `notifications`

#### **4. Ressource (Ressource)**
Hommes et machines de l'entreprise, avec disponibilité.

**Champs:**
- `id`, `nom`, `type` (homme/machine), `specialite`
- `disponible`, `chantierId` (affectation actuelle)
- `indisponibleJusquau`, `raisonIndisponibilite`

#### **5. Pointage (Pointage)**
Affectation quotidienne des ressources aux chantiers.

**Champs:**
- `id`, `date`, `chantierId`, `conducteurId`
- `ressources` (liste avec ressourceId, periode, heuresPrevues)
- `commentaires`, `validePar`, `valideLe`

#### **6. Notification (Notification)**
Système de notifications unifié.

**Champs:**
- `id`, `userId`, `type` (tache/reception/pointage/validation/alerte)
- `entityType`, `entityId`, `titre`, `message`, `url`
- `lue`, `telegramMessageId`, `createdAt`

---

## 🏗️ Architecture Frontend

### **Structure des fichiers**

```
/app/dashboard/chantiers/[id]/
├── page.tsx (onglets étendus - 8 onglets)
└── components/
    ├── SituationsTable.tsx (existant)
    ├── DepensesTable.tsx (existant)
    ├── OperationsList.tsx (existant)
    ├── Indicateurs.tsx (existant)
    ├── ReceptionsList.tsx (NOUVEAU)
    ├── TachesList.tsx (NOUVEAU)
    ├── PointagesList.tsx (NOUVEAU)
    └── NotificationsPanel.tsx (NOUVEAU)
```

### **Nouveaux onglets**

1. **Situations** (existant) - Facturation client
2. **Dépenses** (existant) - Coûts et fournisseurs
3. **Opérations** (existant) - Suivi terrain + HITL
4. **Réceptions** (NOUVEAU) - Réunions client avec tâches
5. **Tâches** (NOUVEAU) - Tâches direction → conducteur
6. **Pointages** (NOUVEAU) - Affectation ressources
7. **Indicateurs** (existant) - Tableau de bord financier
8. **Audit** (existant) - Historique des modifications

### **Nouveau design des onglets**
Redesign complet avec interface moderne et compacte:
- **Barre horizontale** avec style "onglets Windows" (pas de gris inutile)
- **10 onglets** organisés par priorité d'usage
- **Design minimaliste** avec états visuels clairs (actif/hover/normal)
- **Ordre optimisé**: Réceptions → Tâches → Pointages → Notifications → Sections existantes

### **Composants clés - IMPLÉMENTÉS**

#### **ReceptionsList.tsx** (✅ COMPLÉTÉ)
- Liste des réceptions avec filtres par statut/type
- Modal création/édition réception
- Vue détaillée avec participants, ordre du jour, décisions
- Sous-liste des tâches associées
- Badges statut/type, formatage dates

#### **TachesList.tsx** (✅ COMPLÉTÉ)
- **Vue Kanban** (En attente → En cours → Terminée → Annulée)
- Tableau filtré avec multiples filtres (statut, priorité, type)
- Modal détails avec réponse conducteur, documents, notifications
- Badges priorité/type/statut, système de commentaires

#### **PointagesList.tsx** (✅ COMPLÉTÉ)
- Interface d'affectation quotidienne des ressources
- Tableau avec ressources par pointage (hommes/machines)
- Filtres par date, période, type de ressource
- Statistiques rapides (hommes/machines/heures/taux validation)
- Section notifications Telegram avec workflow bi-directionnel

#### **NotificationsPanel.tsx** (✅ COMPLÉTÉ)
- Système unifié de notifications des 3 fonctionnalités
- Tableau filtré par type/statut avec recherche
- Statistiques (total/non lues/validées/urgentes)
- Workflow Telegram détaillé avec exemples
- Interface création de notifications avec types étendus

---

## 🤖 Extension Bot Telegram Construction

### **Architecture modulaire**

```
/app/services/telegram/
├── construction_bot_service.py (existant - étendu)
├── chantier_workflows_service.py (NOUVEAU)
├── notification_service.py (existant - étendu)
└── workflow_manager.py (NOUVEAU)
```

### **Menu principal étendu**

```
🏗️ GESTION CHANTIERS
├── 📋 Rapport quotidien
├── ⚠️ Signalement problème
├── ✅ Validation étape
├── 📦 Commande matériel
├── 💰 Facturation/Situation
├── 👷 Suivi heures
├── 🤝 Réception client (NOUVEAU)
├── 📝 Tâche direction (NOUVEAU)
├── 👥 Pointage équipe (NOUVEAU)
└── 📄 Upload facture (existant)
```

### **Workflows détaillés**

#### **Workflow Réception Client**
```
1. Bouton "🤝 Réception client"
2. Sélection chantier (liste inline)
3. Collecte multi-canal:
   - Texte: participants, ordre du jour
   - Voix: résumé discussions
   - Photos: avancement travaux
   - PDF: compte-rendu
4. Analyse IA (prototypage: réponse statique)
5. Validation utilisateur
6. Création en base
7. Notification HITL aux gérants
```

#### **Workflow Tâche Direction → Conducteur**
```
1. SaaS (Direction): Création tâche
2. Notification Telegram au conducteur
3. Bot Telegram: Bouton "📝 Répondre"
4. Collecte réponse multi-canal
5. Mise à jour SaaS
6. Notification à la direction
```

#### **Workflow Pointage Quotidien**
```
1. Notification matinale (7h)
2. Interface pointage dans Telegram
3. Sélection chantier → ressources
4. Soumission pointage
5. Validation direction
6. Historique et statistiques
```

### **Navigation ergonomique**

1. **Sélection sous-domaine** → Boutons inline
2. **Sélection chantier** → Liste déroulante inline des chantiers "en cours"
3. **Collecte données** → Interface adaptée au sous-domaine
4. **Validation** → Résumé proposé à l'utilisateur
5. **Confirmation** → Envoi vers validation HITL

---

## 🔄 Workflows de notification

### **Principe:**
À chaque fois qu'un côté (conducteur/gérant) fait une action, l'autre côté reçoit une notification Telegram.

### **Exemples:**

#### **Conducteur → Gérant:**
- 📋 Rapport quotidien envoyé
- ⚠️ Signalement problème
- 🤝 Réception client ajoutée
- 👥 Pointage soumis
- 📝 Réponse à une tâche

#### **Gérant → Conducteur:**
- 📝 Nouvelle tâche assignée
- ✅ Validation d'une opération
- ✅ Validation d'un pointage
- 🔄 Modification planning
- ⚠️ Alerte sécurité/problème

### **Format des notifications:**
```
📋 *Nouvelle tâche assignée*

*Titre:* Envoyer photos avancement peinture
*Description:* Photos des pièces principales après finition
*Échéance:* 18/04 17:00
*Priorité:* Moyenne

[Voir dans l'application](https://app.surensaas.com/dashboard/chantiers/crf-001?tab=taches)
```

---

## ✅ Système de validation

### **Principe:**
Les gérants valident ce qu'ils voient dans la page détails reçue en notification.

### **Éléments à valider:**
1. **Opérations terrain** (existant)
2. **Pointages** ressources
3. **Réceptions client** (décisions, points à régler)
4. **Tâches terminées** par les conducteurs
5. **Situations** facturées
6. **Dépenses** importantes

### **Processus:**
1. Notification Telegram avec lien vers page détail
2. Consultation dans le SaaS
3. Validation/rejet avec commentaire
4. Notification retour à l'expéditeur
5. Mise à jour statut et audit trail

---

## 📈 Dashboard amélioré

### **Widget "À valider"**
Agrégation des éléments à valider par sous-domaine:
- 📋 X rapports quotidiens
- ⚠️ Y signalements problèmes
- 🤝 Z réceptions client
- 👥 N pointages
- 📝 M tâches terminées

### **Widget "Alertes"**
Éléments nécessitant attention:
- 🔴 Échéances critiques (< 24h)
- 🟡 Ressources indisponibles
- 🔵 Tâches en retard
- ⚫ Budget dépassé

### **Widget "Activité récente"**
Notifications et modifications récentes:
- Dernières 24h
- Par utilisateur
- Par chantier

### **Widget "Ressources"**
État des hommes/machines:
- ✅ Disponibles: X/Y
- ⚠️ Indisponibles: raisons
- 📊 Taux d'utilisation

---

## 🗄️ Données statiques (prototypage)

### **Jeu de données complet**

#### **Chantier CRF:**
- 2 réceptions client (1 terminée, 1 en cours)
- 3 tâches génériques (1 terminée, 2 en attente)
- 2 pointages (validés)
- 5 notifications (3 lues, 2 non lues)
- 10 ressources (8 disponibles, 2 indisponibles)

#### **Chantier CH-014:**
- 1 réception problème (terminée)
- 1 tâche action (en cours)

### **Fonctions utilitaires**

```typescript
// Obtention données complètes
getChantierCompletById('chantier-crf-001')

// Notifications utilisateur
getNotificationsUtilisateur('user-mohsan-001')

// Ressources
getRessourcesDisponiblesEntreprise()
getRessourcesChantier('chantier-crf-001')

// Statistiques
getStatsChantierEtendues('chantier-crf-001')
```

---

## 🔧 API Routes (Next.js)

### **Routes étendues**

```
GET    /api/chantiers/[id]/receptions
POST   /api/chantiers/[id]/receptions
GET    /api/chantiers/[id]/receptions/[receptionId]
PUT    /api/chantiers/[id]/receptions/[receptionId]
DELETE /api/chantiers/[id]/receptions/[receptionId]

GET    /api/chantiers/[id]/taches
POST   /api/chantiers/[id]/taches
GET    /api/chantiers/[id]/taches/[tacheId]
PUT    /api/chantiers/[id]/taches/[tacheId]
DELETE /api/chantiers/[id]/taches/[tacheId]

GET    /api/chantiers/[id]/pointages
POST   /api/chantiers/[id]/pointages
GET    /api/chantiers/[id]/pointages/[pointageId]
PUT    /api/chantiers/[id]/pointages/[pointageId]
DELETE /api/chantiers/[id]/pointages/[pointageId]

GET    /api/notifications
PUT    /api/notifications/[notificationId]/read
GET    /api/ressources
PUT    /api/ressources/[ressourceId]
```

### **Format de réponse:**
```json
{
  "success": true,
  "data": { /* données */ },
  "message": "Opération réussie"
}
```

---

## 🚀 Plan d'implémentation

### **Phase 1: Foundation (COMPLÉTÉE)**
- ✅ Types TypeScript étendus
- ✅ Données statiques complètes
- ✅ Documentation initiale

### **Phase 2: Frontend MVP (EN COURS)**
- 🔄 Composant ReceptionsList
- 🔄 Composant TachesList
- 🔄 Composant PointagesList
- 🔄 Composant NotificationsPanel
- 🔄 Page détail étendue (8 onglets)
- 🔄 Dashboard amélioré

### **Phase 3: Backend Next.js**
- 🔄 API routes étendues
- 🔄 Système notifications mocké
- 🔄 Calculs d'agrégation

### **Phase 4: Documentation & Intégration**
- 🔄 Guide utilisateur
- 🔄 Spécifications Telegram bot
- 🔄 Tests utilisateur
- 🔄 Préparation production

---

## 📋 Checklist validation

### **Frontend:**
- [ ] Types TypeScript étendus
- [ ] Données statiques complètes
- [ ] Composants ReceptionsList fonctionnel
- [ ] Composants TachesList avec assignation
- [ ] Composants PointagesList avec calendrier
- [ ] NotificationsPanel opérationnel
- [ ] Dashboard avec widgets
- [ ] Navigation entre 8 onglets
- [ ] Responsive design

### **Backend Next.js:**
- [ ] API routes pour nouvelles entités
- [ ] Système de notifications mocké
- [ ] Calculs d'agrégation
- [ ] Simulation workflows Telegram

### **Documentation:**
- [ ] Guide utilisateur nouveaux workflows
- [ ] Spécifications techniques
- [ ] Plan d'intégration Telegram détaillé
- [ ] Mise à jour IMPLEMENTATION_SUMMARY.md

---

## 🔗 Points d'intégration future

### **Avec système existant:**
1. **Base de données** - Nouvelles tables PostgreSQL
2. **Bot Telegram** - Extension ConstructionBotService
3. **Authentification** - Liens utilisateurs Telegram
4. **Notifications** - Service existant étendu

### **Migration progressive:**
1. **Prototypage statique** - Validation UX/UI
2. **Intégration données réelles** - PostgreSQL
3. **Workflows réels** - Bot Telegram
4. **Notifications temps réel** - WebSocket/Telegram

---

## 🎯 Valeur ajoutée

### **Pour les gérants (SaaS):**
- **Vue unifiée** de tous les sous-domaines
- **Tableau de bord** avec indicateurs temps réel
- **Système de validation** centralisé
- **Notifications ciblées** pour actions requises
- **Historique complet** des interactions

### **Pour les conducteurs (Telegram):**
- **Interface simple** et intuitive
- **Collecte multi-canal** sans friction
- **Navigation guidée** avec feedback
- **Notifications contextuelles**
- **Validation en 2 clics**

### **Pour l'entreprise:**
- **Traçabilité complète** des chantiers
- **Optimisation ressources** hommes/machines
- **Réduction appels téléphoniques**
- **Amélioration communication** direction/terrain
- **Base pour IA** future (prédictions, alertes)

---

## 📞 Contact et support

**Documentation technique:** Cette documentation
**Développement:** Phase 2 (Frontend MVP) en cours
**Statut:** Prototypage avec données statiques
**Prochaine étape:** Création des composants frontend

*Dernière mise à jour: 21/04/2026*