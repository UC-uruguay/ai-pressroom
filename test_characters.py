#!/usr/bin/env python3
"""
Test character-based debate generation.
"""
from datetime import datetime
from src.agents.debate_orchestrator import DebateOrchestrator
from src.nlp.summarize import DebateTopic

def main():
    """Test debate generation with new character settings."""
    # Create a simple test topic
    topic = DebateTopic(
        title="AIは人間の仕事を奪うのか？",
        summary="AI技術の発展により、多くの仕事が自動化される可能性がある一方、新しい職種も生まれている。AIと雇用の関係について議論する。",
        key_points=[
            "AIによる自動化で多くの仕事が消滅する可能性",
            "新しい職種や産業が生まれる機会",
            "人間にしかできない仕事の価値"
        ],
        source_articles=["テスト記事"]
    )

    # Initialize orchestrator
    orchestrator = DebateOrchestrator(date=datetime.now())

    print("=" * 60)
    print("キャラクター設定テスト")
    print("=" * 60)
    print()

    # Display role assignments
    print("【本日の役割割り当て】")
    for assignment in orchestrator.role_assignments:
        char = orchestrator.characters.get(assignment.speaker, {})
        persona = char.get("persona_name", "N/A")
        print(f"  {assignment.speaker:8} -> {assignment.role:15} ({persona})")
    print()

    # Generate debate script
    print("【討論スクリプトを生成中...】")
    print()

    try:
        script = orchestrator.generate_script(topic, target_duration_min=3)

        print("=" * 60)
        print(f"トピック: {script.title}")
        print("=" * 60)
        print()

        for i, line in enumerate(script.lines, 1):
            char = orchestrator.characters.get(line.speaker, {})
            persona = char.get("persona_name", line.speaker)

            print(f"{i:2}. [{persona}]")
            print(f"    {line.text}")
            print()

        print("=" * 60)
        print(f"総発言数: {len(script.lines)}")
        print(f"推定時間: {script.total_duration_sec:.1f}秒")
        print("=" * 60)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
