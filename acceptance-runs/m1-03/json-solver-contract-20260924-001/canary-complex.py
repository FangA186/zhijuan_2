"""Authorized live stage probe through Hermes; does not replace the current exam."""
import json
from pathlib import Path
from services.api.settings import settings
from services.api.store import store
from services.exam.question_service import QuestionService

p=Path(__file__).parent
events=[]
spec=store.get_canonical_spec()
slot=next(s for s in store.get_blueprint()['slots'] if s['order']==19)
try:
    result=QuestionService.generate_slot_result('q19',spec=spec,slot=slot,run_event=lambda e:events.append(e))
    summary={'status':'RESULT_RETURNED','validation':result['validation']['overall_status'],
             'events':events,'usage':result['usage']}
except Exception as exc:
    summary={'status':'FAILED','error_type':type(exc).__name__,
             'code':str(exc) if str(exc).startswith('HERMES_') else 'local_validation_failed','events':events}
(p/'canary-complex-result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print({k:v for k,v in summary.items() if k not in {'events','usage'}})
