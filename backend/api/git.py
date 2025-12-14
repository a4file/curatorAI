from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import os
from pathlib import Path

router = APIRouter(prefix="/api/git", tags=["git"])


class GitStatusResponse(BaseModel):
    branch: str
    is_clean: bool
    modified_files: List[str]
    untracked_files: List[str]
    staged_files: List[str]
    status_output: str


class GitLogResponse(BaseModel):
    commits: List[dict]
    total: int


class GitDiffResponse(BaseModel):
    diff: str
    file: Optional[str] = None


class GitCommandRequest(BaseModel):
    command: str
    args: Optional[List[str]] = None


def get_repo_root() -> Path:
    """현재 프로젝트의 git 저장소 루트 경로 반환"""
    current_file = Path(__file__).resolve()
    backend_dir = current_file.parent.parent
    base_dir = backend_dir.parent
    return base_dir


def run_git_command(command: str, args: Optional[List[str]] = None, check: bool = False) -> tuple[str, int]:
    """Git 명령어 실행
    
    Args:
        command: git 명령어 (예: 'status', 'log', 'diff')
        args: 추가 인자 리스트
        check: True면 오류 시 예외 발생
    
    Returns:
        (output, return_code) 튜플
    """
    repo_root = get_repo_root()
    
    git_cmd = ['git', command]
    if args:
        git_cmd.extend(args)
    
    try:
        result = subprocess.run(
            git_cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, git_cmd, result.stderr)
        
        return result.stdout, result.returncode
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Git이 설치되어 있지 않습니다.")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Git 명령어 실행 실패: {e.stderr}")


@router.get("/status", response_model=GitStatusResponse)
async def get_git_status():
    """Git 저장소 상태 확인"""
    output, return_code = run_git_command('status', ['--porcelain'])
    status_output, _ = run_git_command('status')
    
    # 브랜치 정보 가져오기
    branch_output, _ = run_git_command('branch', ['--show-current'])
    branch = branch_output.strip() or 'unknown'
    
    # 파일 상태 파싱
    modified_files = []
    untracked_files = []
    staged_files = []
    
    for line in output.strip().split('\n'):
        if not line:
            continue
        
        status = line[:2]
        filename = line[3:].strip()
        
        if status.startswith('??'):
            untracked_files.append(filename)
        elif status[0] in ['A', 'M', 'D']:
            staged_files.append(filename)
        elif status[1] in ['M', 'D']:
            modified_files.append(filename)
    
    is_clean = len(modified_files) == 0 and len(untracked_files) == 0 and len(staged_files) == 0
    
    return GitStatusResponse(
        branch=branch,
        is_clean=is_clean,
        modified_files=modified_files,
        untracked_files=untracked_files,
        staged_files=staged_files,
        status_output=status_output.strip()
    )


@router.get("/log", response_model=GitLogResponse)
async def get_git_log(limit: int = 20, file: Optional[str] = None):
    """Git 커밋 로그 조회
    
    Args:
        limit: 반환할 커밋 수 (기본값: 20)
        file: 특정 파일의 로그만 조회 (선택적)
    """
    args = ['--oneline', '--decorate', f'-n{limit}']
    if file:
        args.append('--')
        args.append(file)
    
    output, _ = run_git_command('log', args)
    
    commits = []
    for line in output.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split(' ', 1)
        if len(parts) == 2:
            commit_hash = parts[0]
            message = parts[1]
            commits.append({
                'hash': commit_hash,
                'message': message
            })
    
    return GitLogResponse(
        commits=commits,
        total=len(commits)
    )


@router.get("/diff", response_model=GitDiffResponse)
async def get_git_diff(file: Optional[str] = None, staged: bool = False):
    """Git diff 조회
    
    Args:
        file: 특정 파일의 diff만 조회 (선택적)
        staged: staged 변경사항 조회 여부
    """
    args = []
    if staged:
        args.append('--staged')
    if file:
        args.append('--')
        args.append(file)
    
    output, _ = run_git_command('diff', args)
    
    return GitDiffResponse(
        diff=output,
        file=file
    )


@router.get("/branch")
async def get_branches():
    """모든 브랜치 목록 조회"""
    output, _ = run_git_command('branch', ['-a'])
    branches = [line.strip().lstrip('* ').strip() for line in output.strip().split('\n') if line.strip()]
    
    current_output, _ = run_git_command('branch', ['--show-current'])
    current = current_output.strip()
    
    return {
        'current': current,
        'branches': branches
    }


@router.get("/remote")
async def get_remotes():
    """원격 저장소 정보 조회"""
    output, _ = run_git_command('remote', ['-v'])
    remotes = {}
    
    for line in output.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) == 2:
            name = parts[0]
            url = parts[1].split()[0]
            remotes[name] = url
    
    return {
        'remotes': remotes
    }


@router.post("/command")
async def execute_git_command(request: GitCommandRequest):
    """Git 명령어 실행 (제한적)
    
    주의: 보안상 위험한 명령어는 차단됩니다.
    """
    # 위험한 명령어 차단
    dangerous_commands = ['push', 'force', 'reset', 'rebase', 'merge', 'checkout', 'commit']
    if any(cmd in request.command.lower() for cmd in dangerous_commands):
        raise HTTPException(
            status_code=403,
            detail="보안상의 이유로 해당 명령어는 실행할 수 없습니다."
        )
    
    output, return_code = run_git_command(request.command, request.args)
    
    return {
        'command': f"git {request.command} {' '.join(request.args or [])}",
        'output': output,
        'return_code': return_code,
        'success': return_code == 0
    }

