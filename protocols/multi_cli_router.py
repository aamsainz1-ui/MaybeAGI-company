#!/usr/bin/env python3
"""
Multi-Agent CLI Router
Routes tasks to the best CLI: Claude / Codex / Gemini
+ Oracle memory integration
"""
import subprocess, json, requests, re
from pathlib import Path

ORACLE_URL = "http://localhost:47778"
LESSONS_DIR = Path("/root/.openclaw/workspace/memory/lessons")

# Routing table: task type → CLI + model
ROUTING = {
    "finance":    {"cli": "claude", "args": ["--print"], "desc": "CFO-level financial analysis"},
    "marketing":  {"cli": "claude", "args": ["--print"], "desc": "CMO-level marketing analysis"},
    "operations": {"cli": "claude", "args": ["--print"], "desc": "COO-level operations"},
    "research":   {"cli": "claude", "args": ["--print"], "desc": "World-class research analyst"},
    "code":       {"cli": "codex",  "args": ["--approval-mode", "full-auto"], "desc": "Expert software engineer"},
    "technical":  {"cli": "codex",  "args": ["--approval-mode", "full-auto"], "desc": "Technical implementation"},
    "creative":   {"cli": "claude", "args": ["--print"], "desc": "Creative strategy"},
    "memory":     {"cli": "claude", "args": ["--print"], "desc": "Knowledge architect"},
}

def get_oracle_context(task: str, limit: int = 3) -> str:
    """ดึง context จาก Oracle"""
    try:
        r = requests.get(f"{ORACLE_URL}/api/search", params={"q": task, "limit": limit}, timeout=5)
        results = r.json().get("results", [])
        if not results:
            return ""
        context = "\n## Relevant Past Experience (from Oracle Memory):\n"
        for i, res in enumerate(results, 1):
            context += f"{i}. {res.get('content', '')[:150]}\n"
        return context
    except:
        return ""

def detect_task_type(prompt: str) -> str:
    """Auto-detect task type from prompt"""
    prompt_lower = prompt.lower()
    if any(w in prompt_lower for w in ["revenue", "profit", "cash", "budget", "expense", "payment", "financial"]):
        return "finance"
    if any(w in prompt_lower for w in ["campaign", "conversion", "traffic", "ads", "marketing", "growth", "ctr", "cac"]):
        return "marketing"
    if any(w in prompt_lower for w in ["workflow", "bottleneck", "deadline", "task", "team", "operations", "process"]):
        return "operations"
    if any(w in prompt_lower for w in ["code", "script", "python", "javascript", "bug", "function", "api"]):
        return "code"
    if any(w in prompt_lower for w in ["research", "compare", "competitor", "analysis", "find", "what is"]):
        return "research"
    return "finance"  # default to claude

def run_agent(task_type: str, prompt: str, agent_prompt_file: str = None) -> str:
    """Run specialist agent with Oracle context injected"""
    route = ROUTING.get(task_type, ROUTING["research"])
    
    # Load agent system prompt
    system_prompt = ""
    if agent_prompt_file:
        path = Path(f"/root/.openclaw/workspace/agent_system/core/{agent_prompt_file}.txt")
        if path.exists():
            system_prompt = path.read_text()[:1000]  # cap to save tokens
    
    # Get Oracle context
    oracle_ctx = get_oracle_context(f"{task_type} {prompt[:50]}")
    
    # Build full prompt
    full_prompt = f"{system_prompt}\n{oracle_ctx}\n\n## Task:\n{prompt}"
    
    cli = route["cli"]
    args = route["args"]
    
    try:
        if cli == "claude":
            result = subprocess.run(
                ["claude", "--print", "-p", full_prompt],
                capture_output=True, text=True, timeout=60
            )
        elif cli == "codex":
            result = subprocess.run(
                ["codex", "--approval-mode", "full-auto", "-q", full_prompt],
                capture_output=True, text=True, timeout=120
            )
        else:
            result = subprocess.run(
                [cli] + args + [full_prompt],
                capture_output=True, text=True, timeout=60
            )
        return result.stdout.strip()
    except Exception as e:
        return f"Error running {cli}: {e}"

def auto_sync_lesson(task_type: str, task: str, result: str, success: bool):
    """Auto-sync lesson to Oracle after task"""
    import datetime
    lesson_id = f"{task_type.upper()[:3]}-LRN-{datetime.date.today().strftime('%Y%m%d')}"
    
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = LESSONS_DIR / f"{lesson_id}.md"
    
    content = f"""# {lesson_id}
**Task Type:** {task_type}
**Date:** {datetime.date.today()}
**Success:** {success}

## Task
{task[:200]}

## Result Summary
{result[:300]}

## Lesson
{"Task completed successfully" if success else "Task encountered issues - review approach"}

## Reusable Rule
{"Apply {task_type} agent for similar tasks" if success else "Review {task_type} agent prompt for improvements"}
"""
    filepath.write_text(content)
    
    # Sync to Oracle bridge
    bridge_path = Path("/root/.openclaw/workspace/integrations/oracle/runtime/bridge/ψ/memory/resonance")
    if bridge_path.exists():
        (bridge_path / filepath.name).write_text(content)
    
    return str(filepath)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        task_input = " ".join(sys.argv[1:])
    else:
        task_input = "Analyze marketing campaign performance and suggest improvements"
    
    task_type = detect_task_type(task_input)
    agent_map = {
        "finance": "finance_agent",
        "marketing": "marketing_agent", 
        "operations": "operations_agent",
        "research": "research_agent",
        "code": None,
    }
    
    print(f"🔀 Routing to: {task_type} agent ({ROUTING[task_type]['cli']})")
    print(f"📚 Fetching Oracle context...")
    
    result = run_agent(task_type, task_input, agent_map.get(task_type))
    print(f"\n{'='*50}")
    print(result)
    print(f"{'='*50}")
    
    # Auto-sync lesson
    lesson_path = auto_sync_lesson(task_type, task_input, result, bool(result))
    print(f"\n✅ Lesson stored: {lesson_path}")
