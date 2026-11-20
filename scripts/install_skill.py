"""Install the portable Gaia XP skill in a research project's agent directories."""

import argparse
import shutil
import tempfile
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "skills" / "gaia-xp-fit"
LOCATIONS = {
    "codex": ".agents",
    "cursor": ".agents",
    "gemini-cli": ".agents",
    "opencode": ".agents",
    "deepseek": ".agents",
    "pi": ".agents",
    "antigravity": ".agents",
    "openclaw": ".agents",
    "claude-code": ".claude",
    "cline": ".claude",
    "github-copilot": ".github",
    "windsurf": ".windsurf",
}


def identical(source, target):
    if target.is_symlink() or target.is_junction():
        return False
    if source.is_file():
        return (target.is_file() and source.stat().st_size == target.stat().st_size
                and source.read_bytes() == target.read_bytes())
    if not target.is_dir():
        return False
    entries = list(source.iterdir())
    if {path.name for path in target.iterdir()} != {path.name for path in entries}:
        return False
    return all(identical(entry, target / entry.name) for entry in entries)


def already_installed(target):
    if target.is_dir() and identical(SOURCE, target.resolve()):
        return True
    if target.exists() or target.is_symlink() or target.is_junction():
        raise FileExistsError(f"Different skill or file already exists at {target}")
    return False


def install(project, agents):
    project = project.expanduser().resolve(strict=True)
    if not project.is_dir():
        raise NotADirectoryError(f"Expected a project directory: {project}")
    if not (SOURCE / "SKILL.md").is_file():
        raise FileNotFoundError(f"Missing skill in checkout: {SOURCE}")
    selected = LOCATIONS if "all" in agents else agents
    targets = [project / root / "skills" / SOURCE.name
               for root in dict.fromkeys(LOCATIONS[agent] for agent in selected)]
    # 落盘前先检查所有选定位置，保留研究项目中原有的同名 skill。
    for target in targets:
        if not target.parent.resolve().is_relative_to(project):
            raise ValueError(f"Skill directory points outside the selected project: {target.parent}")
        for parent in (target.parent.parent, target.parent):
            if parent.exists() and not parent.is_dir():
                raise NotADirectoryError(f"Expected a directory: {parent}")
        already_installed(target)

    for target in targets:
        if already_installed(target):
            print(f"Already installed: {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # 完整复制后再公布目录，使重试可复用已完成的安装。
        with tempfile.TemporaryDirectory(prefix=".gaia-xp-stage-", dir=target.parent) as temporary:
            staged = Path(temporary) / SOURCE.name
            shutil.copytree(SOURCE, staged)
            try:
                staged.rename(target)
            except OSError:
                if not already_installed(target):
                    raise
                print(f"Already installed: {target}")
                continue
        print(f"Installed: {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd(),
                        help="existing research folder (default: current directory)")
    parser.add_argument("--agent", choices=[*LOCATIONS, "all"], action="extend", nargs="+",
                        required=True, help="one or more agents sharing the research folder")
    args = parser.parse_args()
    try:
        install(args.project, args.agent)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Installation failed: {error}\n")


if __name__ == "__main__":
    main()
