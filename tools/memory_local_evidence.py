"""Missing, explicitly ignored historical artifacts are unavailable, never proof."""
import subprocess
from .memory_base import RecordError, safe_path


def historical_reference(root, ref, warnings, *, strict=False):
    path = safe_path(root, ref)
    if path.is_file():
        return
    # Only the repository's explicit acceptance-artifact exclusion is eligible.
    ignored = False
    if not path.exists() and ref.startswith('acceptance-runs/') and (root / '.git').exists():
        result = subprocess.run(['git', '-C', str(root), 'check-ignore', '--no-index', '-q', '--', ref],
                                capture_output=True, check=False)
        tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--error-unmatch', '--', ref],
                                 capture_output=True, check=False).returncode == 0
        ignored = result.returncode == 0 and not tracked
    if strict or not ignored:
        raise RecordError('Missing required file: ' + ref)
    message = f'LOCAL_EVIDENCE_UNAVAILABLE: {ref}（按Git规则留在本地，当前检出无法验证历史结论）'
    if message not in warnings:
        warnings.append(message)
