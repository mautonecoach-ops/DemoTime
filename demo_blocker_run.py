# demo_blocker_run.py
# Script de prueba para ver el Blocker en acción.

from lexo.blocker import Blocker, BlockerConfig

def demo(metrics, cfg):
    blocker = Blocker(config=cfg)
    block, reasons = blocker.evaluate(metrics)
    print("== Métricas ==", metrics)
    print("== Config   ==", cfg)
    if block:
        print("🚫 BLOQUEADO por:", "; ".join(reasons))
    else:
        if reasons:
            print("⚠️  AVISO (no bloquea):", "; ".join(reasons))
        else:
            print("✅ OK: no hay motivos de bloqueo.")

if __name__ == "__main__":
    # Caso 1: todo bien
    metrics_ok = {"trust": 70.0, "cohesion": 40.0, "equity": 75.0}
    demo(metrics_ok, BlockerConfig())

    print("\n---\n")

    # Caso 2: falla cohesión (bloquea)
    metrics_fail = {"trust": 65.0, "cohesion": 20.0, "equity": 60.0}
    demo(metrics_fail, BlockerConfig())

    print("\n---\n")

    # Caso 3: mismo fallo pero en dry-run (no bloquea, solo avisa)
    demo(metrics_fail, BlockerConfig(dry_run=True))
