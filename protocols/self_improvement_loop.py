#!/usr/bin/env python3
"""
Self-Improving Agent Loop
Task → Action → Result → Review → Learning → Memory Update
"""
import json, datetime, requests
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
LESSONS_DIR = WORKSPACE / "memory/lessons"
ORACLE_URL = "http://localhost:47778"

LESSONS_DIR.mkdir(parents=True, exist_ok=True)

def get_relevant_lessons(task_type: str, situation: str) -> list:
    """ดึง lessons เก่าจาก Oracle ก่อนเริ่ม task"""
    try:
        r = requests.get(f"{ORACLE_URL}/api/search", 
                        params={"q": f"{task_type} {situation}", "limit": 3},
                        timeout=5)
        results = r.json().get("results", [])
        return [r.get("content", "") for r in results]
    except:
        return []

def store_lesson(lesson: dict):
    """บันทึก lesson หลัง task เสร็จ"""
    lesson_id = lesson.get("lesson_id", f"LRN-{datetime.date.today().strftime('%Y%m%d')}-{len(list(LESSONS_DIR.glob('*.md')))}")
    
    content = f"""# {lesson_id}

**Task Type:** {lesson.get('task_type', '')}
**Date:** {datetime.date.today()}
**Classification:** {lesson.get('classification', 'Lesson')}

## Situation
{lesson.get('situation', '')}

## Action Taken
{lesson.get('action_taken', '')}

## Outcome
{lesson.get('outcome', '')}

## Lesson
{lesson.get('lesson', '')}

## Confidence
{lesson.get('confidence', 'Medium')}

## Reusable Rule
{lesson.get('reusable_rule', '')}
"""
    filepath = LESSONS_DIR / f"{lesson_id}.md"
    filepath.write_text(content, encoding='utf-8')
    print(f"✅ Lesson stored: {filepath}")
    return str(filepath)

def post_task_reflection(objective: str, actions: str, successes: str, 
                         weaknesses: str, lessons: str, task_type: str = "general") -> dict:
    """สร้าง reflection report และ store lesson ถ้า high-value"""
    
    report = {
        "objective": objective,
        "actions_taken": actions,
        "successes": successes,
        "weaknesses": weaknesses,
        "lessons_learned": lessons,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Store เฉพาะ lesson ที่มีคุณค่า (ไม่ใช่ noise)
    if weaknesses.strip() or lessons.strip():
        lesson = {
            "lesson_id": f"{task_type.upper()[:3]}-LRN-{datetime.date.today().strftime('%Y%m%d')}",
            "task_type": task_type,
            "situation": objective,
            "action_taken": actions,
            "outcome": successes,
            "lesson": lessons,
            "confidence": "High" if successes and not weaknesses else "Medium",
            "reusable_rule": lessons.split('.')[0] if lessons else "",
            "classification": "Lesson"
        }
        store_lesson(lesson)
    
    return report

def inject_context_for_task(task_type: str, situation: str) -> str:
    """ดึง context จาก Oracle มา inject ก่อน spawn agent"""
    lessons = get_relevant_lessons(task_type, situation)
    if not lessons:
        return ""
    
    context = f"\n\n## Relevant Past Lessons\n"
    for i, l in enumerate(lessons, 1):
        context += f"{i}. {l[:200]}\n"
    return context

if __name__ == "__main__":
    # ทดสอบ
    print("Testing Self-Improving Loop...")
    
    # Inject context ก่อน task
    context = inject_context_for_task("marketing", "conversion drop")
    print(f"Context injected: {len(context)} chars")
    
    # หลัง task เสร็จ — store reflection
    report = post_task_reflection(
        objective="วิเคราะห์ football tipster pipeline",
        actions="สร้าง Multi-AI filter: Claude→Gemini→GPT",
        successes="3/3 tips ผ่าน filter, ส่ง Telegram สำเร็จ",
        weaknesses="Gemini CLI ค้าง ต้องใช้ Claude แทน",
        lessons="Gemini CLI ไม่เหมาะกับ non-interactive mode ใช้ claude --print แทนทุก layer",
        task_type="BALL"
    )
    print(f"Reflection stored: {report['timestamp']}")
