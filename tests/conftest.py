import sys
from pathlib import Path

# Asegura que src/ esté en el path incluso si el paquete no está instalado en modo editable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
