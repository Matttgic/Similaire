#!/usr/bin/env python3
"""
Script de sauvegarde de la base de données
"""

import sys
import os
import shutil
import argparse
from datetime import datetime
import sqlite3

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config

def create_backup(source_db, backup_dir=None):
    """Crée une sauvegarde de la base de données"""
    
    if not os.path.exists(source_db):
        print(f"❌ Base de données source non trouvée: {source_db}")
        return False
    
    # Créer le répertoire de sauvegarde si nécessaire
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(source_db), 'backups')
    
    os.makedirs(backup_dir, exist_ok=True)
    
    # Nom du fichier de sauvegarde avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"football_odds_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Copier la base de données
        shutil.copy2(source_db, backup_path)
        
        # Vérifier l'intégrité de la sauvegarde
        if verify_backup(backup_path):
            print(f"✅ Sauvegarde créée avec succès: {backup_path}")
            
            # Afficher les statistiques
            show_backup_stats(backup_path)
            
            return backup_path
        else:
            print(f"❌ Erreur de vérification de la sauvegarde")
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        return False

def verify_backup(backup_path):
    """Vérifie l'intégrité d'une sauvegarde"""
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # Vérifier l'intégrité de la base
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        conn.close()
        
        return result == "ok"
        
    except Exception as e:
        print(f"❌ Erreur de vérification: {e}")
        return False

def show_backup_stats(backup_path):
    """Affiche les statistiques de la sauvegarde"""
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # Taille du fichier
        file_size = os.path.getsize(backup_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Statistiques des tables
        cursor.execute("SELECT COUNT(*) FROM matches")
        total_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM matches WHERE is_settled = TRUE")
        settled_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT league_id) FROM matches")
        total_leagues = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(start_time), MAX(start_time) FROM matches")
        date_range = cursor.fetchone()
        
        conn.close()
        
        print(f"📊 Statistiques de la sauvegarde:")
        print(f"   💾 Taille: {file_size_mb:.2f} MB")
        print(f"   ⚽ Total matchs: {total_matches}")
        print(f"   ✅ Matchs terminés: {settled_matches}")
        print(f"   🏆 Ligues: {total_leagues}")
        if date_range[0] and date_range[1]:
            print(f"   📅 Période: {date_range[0][:10]} à {date_range[1][:10]}")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'affichage des stats: {e}")

def cleanup_old_backups(backup_dir, keep_days=30):
    """Supprime les anciennes sauvegardes"""
    if not os.path.exists(backup_dir):
        return
    
    cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
    deleted_count = 0
    
    for filename in os.listdir(backup_dir):
        if filename.startswith('football_odds_backup_') and filename.endswith('.db'):
            file_path = os.path.join(backup_dir, filename)
            file_time = os.path.getmtime(file_path)
            
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"🗑️ Supprimé: {filename}")
                except Exception as e:
                    print(f"❌ Erreur suppression {filename}: {e}")
    
    if deleted_count > 0:
        print(f"✅ {deleted_count} anciennes sauvegardes supprimées")
    else:
        print("ℹ️ Aucune ancienne sauvegarde à supprimer")

def list_backups(backup_dir):
    """Liste les sauvegardes disponibles"""
    if not os.path.exists(backup_dir):
        print("❌ Répertoire de sauvegarde non trouvé")
        return
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.startswith('football_odds_backup_') and filename.endswith('.db'):
            file_path = os.path.join(backup_dir, filename)
            file_size = os.path.getsize(file_path)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            backups.append({
                'filename': filename,
                'path': file_path,
                'size': file_size,
                'date': file_time
            })
    
    if not backups:
        print("ℹ️ Aucune sauvegarde trouvée")
        return
    
    # Trier par date (plus récent en premier)
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    print(f"📋 {len(backups)} sauvegarde(s) disponible(s):")
    for backup in backups:
        size_mb = backup['size'] / (1024 * 1024)
        print(f"   📁 {backup['filename']}")
        print(f"      📅 {backup['date'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      💾 {size_mb:.2f} MB")
        print()

def restore_backup(backup_path, target_db):
    """Restaure une sauvegarde"""
    if not os.path.exists(backup_path):
        print(f"❌ Sauvegarde non trouvée: {backup_path}")
        return False
    
    if not verify_backup(backup_path):
        print(f"❌ Sauvegarde corrompue: {backup_path}")
        return False
    
    # Créer une sauvegarde de la base actuelle avant restauration
    if os.path.exists(target_db):
        current_backup = create_backup(target_db)
        if current_backup:
            print(f"🔄 Base actuelle sauvegardée: {current_backup}")
    
    try:
        shutil.copy2(backup_path, target_db)
        print(f"✅ Restauration réussie: {backup_path} -> {target_db}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la restauration: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Gestion des sauvegardes de la base de données')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup'],
                       help='Action à effectuer')
    parser.add_argument('--source', default=Config.DATABASE_PATH,
                       help='Chemin de la base source')
    parser.add_argument('--backup-dir', default=None,
                       help='Répertoire des sauvegardes')
    parser.add_argument('--backup-file', default=None,
                       help='Fichier de sauvegarde à restaurer')
    parser.add_argument('--keep-days', type=int, default=30,
                       help='Nombre de jours de rétention pour le nettoyage')
    
    args = parser.parse_args()
    
    # Déterminer le répertoire de sauvegarde
    if args.backup_dir is None:
        args.backup_dir = os.path.join(os.path.dirname(args.source), 'backups')
    
    print(f"🚀 Action: {args.action}")
    print(f"📂 Base source: {args.source}")
    print(f"📁 Répertoire sauvegardes: {args.backup_dir}")
    
    if args.action == 'backup':
        create_backup(args.source, args.backup_dir)
        
    elif args.action == 'list':
        list_backups(args.backup_dir)
        
    elif args.action == 'cleanup':
        cleanup_old_backups(args.backup_dir, args.keep_days)
        
    elif args.action == 'restore':
        if not args.backup_file:
            print("❌ Spécifiez le fichier de sauvegarde avec --backup-file")
            return
        
        backup_path = args.backup_file
        if not os.path.isabs(backup_path):
            backup_path = os.path.join(args.backup_dir, backup_path)
        
        restore_backup(backup_path, args.source)

if __name__ == "__main__":
    main()
