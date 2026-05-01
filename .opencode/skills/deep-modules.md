Skill: Deep Module Architect
Objectif : Maximiser la puissance des interfaces, minimiser la complexité exposée.
Action : Lors de la phase "REFACTOR" du cycle TDD, analyse la structure :

Est-ce que ce module expose trop de fonctions internes ? (Si oui, encapsule).

L'interface est-elle simple (facile à appeler) alors que l'implémentation gère la complexité ?

Évite les "Shallow Modules" (modules qui n'apportent aucune abstraction réelle).
Loi : Préfère un gros module avec une interface élégante à dix petits modules qui s'appellent entre eux de façon confuse.
