export default function DashboardPage() {
  return (
    <div className="p-6 lg:p-8">
      <h1 className="text-3xl font-bold mb-6">Tableau de bord</h1>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="p-6 border rounded-lg bg-card">
          <h3 className="text-sm font-medium text-muted-foreground">Factures ce mois</h3>
          <p className="text-2xl font-bold mt-2">12</p>
        </div>
        
        <div className="p-6 border rounded-lg bg-card">
          <h3 className="text-sm font-medium text-muted-foreground">En attente</h3>
          <p className="text-2xl font-bold mt-2">3</p>
        </div>
        
        <div className="p-6 border rounded-lg bg-card">
          <h3 className="text-sm font-medium text-muted-foreground">Montant total</h3>
          <p className="text-2xl font-bold mt-2">45,230 €</p>
        </div>
        
        <div className="p-6 border rounded-lg bg-card">
          <h3 className="text-sm font-medium text-muted-foreground">Chantiers actifs</h3>
          <p className="text-2xl font-bold mt-2">5</p>
        </div>
      </div>
    </div>
  );
}
