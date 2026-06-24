import asyncio
import time
from rich.console import Console
from rich.live import Live
from rich.text import Text

console = Console()

def _spin(label: str):
    return Live(Text(f"⏳ {label}", style="cyan"), console=console, refresh_per_second=8, transient=True)

async def main():
    print("Testing spin inside async...")
    with _spin("Spinning..."):
        await asyncio.sleep(2)
    print("Done spinning!")

if __name__ == "__main__":
    asyncio.run(main())
