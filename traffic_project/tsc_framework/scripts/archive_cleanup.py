import os
import shutil
import sys

def main():
    project_root = r"C:\Proyecto_Tesis_Final_V1\traffic_project"
    scripts_dir = os.path.join(project_root, "tsc_framework", "scripts")
    archive_dir = os.path.join(scripts_dir, "archive")
    
    print("==================================================")
    # 1. Crear directorio de archivo
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        print(f"✅ Creado directorio de archivo: {archive_dir}")
    else:
        print(f"ℹ️ El directorio de archivo ya existe: {archive_dir}")
        
    print("==================================================")
    print("🧹 FASE 1: Limpieza de tsc_framework/scripts/")
    
    primary_scripts = {
        "run_visual_sim.py",
        "generate_latam_imprudent.py",
        "evaluate.py",
        "train.py",
        "generate_normal_hangzhou.py",
        "archive",
        "__pycache__",
        "archive_cleanup.py"
    }
    
    # Listar y mover archivos de tsc_framework/scripts
    moved_scripts_count = 0
    for item in os.listdir(scripts_dir):
        if item in primary_scripts:
            continue
            
        src_path = os.path.join(scripts_dir, item)
        dst_path = os.path.join(archive_dir, item)
        
        try:
            if os.path.exists(dst_path):
                # Si ya existe en el archivo, añadir sufijo para no sobreescribir destructivamente
                base, ext = os.path.splitext(item)
                counter = 1
                while os.path.exists(os.path.join(archive_dir, f"{base}_{counter}{ext}")):
                    counter += 1
                dst_path = os.path.join(archive_dir, f"{base}_{counter}{ext}")
            
            shutil.move(src_path, dst_path)
            print(f"  -> Archivado: {item} -> {os.path.basename(dst_path)}")
            moved_scripts_count += 1
        except Exception as e:
            print(f"  ❌ Error archivando {item}: {e}")
            
    print(f"✅ Completada Fase 1: {moved_scripts_count} archivos movidos a 'archive/'.")
    
    print("==================================================")
    print("🧹 FASE 2: Purgado de Duplicados en la Raíz")
    
    # Carpetas duplicadas a eliminar en root
    duplicate_dirs = ["scripts", "src"]
    for d in duplicate_dirs:
        dir_path = os.path.join(project_root, d)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"  🗑️ Eliminado directorio duplicado del root: {d}/")
            except Exception as e:
                print(f"  ❌ Error eliminando directorio {d}: {e}")
        else:
            print(f"  ℹ️ No se detectó el directorio duplicado en root: {d}/")
            
    # Mover archivos huérfanos del root a archive/
    orphan_root_files = [
        "debug_maxpressure.py",
        "patch_resco.py",
        "patch_resco_smart.py",
        "prepare_pytsc.py",
        "prepare_resco.py",
        "run_benchmark_suite.py"
    ]
    
    moved_orphans_count = 0
    for f in orphan_root_files:
        src_path = os.path.join(project_root, f)
        if os.path.exists(src_path) and os.path.isfile(src_path):
            dst_path = os.path.join(archive_dir, f)
            try:
                if os.path.exists(dst_path):
                    base, ext = os.path.splitext(f)
                    counter = 1
                    while os.path.exists(os.path.join(archive_dir, f"{base}_{counter}{ext}")):
                        counter += 1
                    dst_path = os.path.join(archive_dir, f"{base}_{counter}{ext}")
                    
                shutil.move(src_path, dst_path)
                print(f"  -> Archivado del root: {f} -> {os.path.basename(dst_path)}")
                moved_orphans_count += 1
            except Exception as e:
                print(f"  ❌ Error moviendo huérfano {f}: {e}")
                
    print(f"✅ Completada Fase 2: {moved_orphans_count} archivos huérfanos archivados.")
    print("==================================================")
    print("🎉 AUDITORÍA Y CONSOLIDACIÓN COMPLETADA SATISFACTORIAMENTE")
    print("==================================================")

if __name__ == "__main__":
    main()
