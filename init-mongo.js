// init-mongo.js - Crée un utilisateur "migration" sur la base "migration_db"
// avec les droits : find, insert, update, delete (pas de création/destruction d'index ou de collection)

const dbName = process.env.DB_NAME;
const roleName = process.env.MG_USERNAME;
const migrationPassword = process.env.MG_PASSWORD;

// Création si inexistant et Connexion à la base cible 
const db = db.getSiblingDB(dbName);

// Rôle personnalisé : uniquement les actions CRUD de base (sans gestion d'index, sans dropCollection, etc.)
const existingRole = db.getRole( roleName, { showBuiltinRoles: false } );

if (!existingRole) { // vérifie si un role existe déjà avec le même nom.
  db.createRole({
    role: roleName,
    privileges: [
      {
        resource: { db: dbName, collection: "" }, // toutes les collections de migration_db
        actions: ["find", "insert", "update"]
      }
    ],
    roles: []
  });
  print(`✅ Rôle '${roleName}' créé sur la base '${dbName}' avec actions find/insert/update/delete`);
} else {
  print(`ℹ️ Le rôle '${roleName}' existe déjà`);
}

// Création de l'utilisateur
const existingUser = db.getUser("migration");
if (!existingUser) {
  db.createUser({
    user: "migration",
    pwd: migrationPassword,
    roles: [{ role: roleName, db: dbName }]
  });
  print(`✅ Utilisateur 'migration' créé sur '${dbName}' avec le rôle '${roleName}'`);
} else {
  print(`ℹ️ L'utilisateur 'migration' existe déjà`);
}