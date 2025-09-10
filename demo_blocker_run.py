# demo_blocker_run.py - Demo v0.2
from lexo.blocker import Blocker, BlockerConfig, BlockerPolicy

def run_case(title, metrics, cfg):
    print(f"\n== {title} ==")
    blocker = Blocker(config=cfg)
    block, reasons = blocker.evaluate(metrics)
    print("Métricas:", metrics)
    print("Config  :", cfg)
    if block:
        print("🚫 BLOQUEADO:", "; ".join(reasons))
    else:
        if reasons:
            print("⚠️  AVISO   :", "; ".join(reasons))
        else:
            print("✅ OK        : sin motivos de bloqueo.")

if __name__ == "__main__":
    # Política base (similar v0.1)
    pol_base = BlockerPolicy(
        min={"trust": 50, "cohesion": 30, "equity": 50},
        weights={"trust": 1/3, "cohesion": 1/3, "equity": 1/3},
        require_fail_count=1,
        score_threshold=None,
    )
    cfg_base = BlockerConfig(policy=pol_base, dry_run=False)

    run_case("Caso OK", {"trust": 70, "cohesion": 40, "equity": 75}, cfg_base)
    run_case("Falla cohesión", {"trust": 65, "cohesion": 20, "equity": 60}, cfg_base)

    # Política más estricta con score mínimo y más peso a cohesión
    pol_strict = BlockerPolicy(
        min={"trust": 50, "cohesion": 40, "equity": 60},
        weights={"trust": 0.25, "cohesion": 0.5, "equity": 0.25},
        require_fail_count=2,       # bloquear si fallan 2 o más
        score_threshold=80.0,       # y además exigir score ≥ 80
    )
    cfg_strict = BlockerConfig(policy=pol_strict, dry_run=False)

    run_case("Política estricta (puede bloquear por score)", {"trust": 60, "cohesion": 38, "equity": 65}, cfg_strict)

    # Modo dry-run (no bloquea, avisa)
    cfg_dry = BlockerConfig(policy=pol_strict, dry_run=True)
    run_case("Dry-run (avisa)", {"trust": 48, "cohesion": 35, "equity": 58}, cfg_dry)
