import unittest
from dataclasses import replace
from reference_code.publish_gate import (
    Approval, Check, Resolution, Status, evaluate_publish,
)

class PublishGateTests(unittest.TestCase):
    def base(self):
        return dict(
            content_hash="paper-current",
            required_checks={"question:q1:structure":"q1-current","render:student:preflight":"render-current"},
            checks=(Check("c1","question:q1:structure","q1-current",Status.PASS,False,True),
                    Check("c2","render:student:preflight","render-current",Status.PASS,False,True)),
            resolutions=(),
            content_approvals=(Approval("paper-current","reviewer-1",True),),
            render_hashes=("render-current",),
            render_approvals=(Approval("render-current","reviewer-1",True),),
            authorized_reviewer_ids=frozenset({"author","reviewer-1","reviewer-2","reviewer-3"}),
            content_author_ids=frozenset({"author"}),
            min_content_reviewers=1,
            require_separation=True,
            complete=True,
            policy_allows_use=True,
        )
    def test_pass(self):
        self.assertTrue(evaluate_publish(**self.base()).allowed)
    def test_fail_cannot_be_waived(self):
        x=self.base(); x['checks']=(replace(x['checks'][0],status=Status.FAIL,manual_allowed=True),x['checks'][1])
        x['resolutions']=(Resolution('c1','q1-current','reviewer-1','已阅读',True),)
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_review_requires_resolution(self):
        x=self.base(); x['checks']=(replace(x['checks'][0],status=Status.REVIEW,manual_allowed=True),x['checks'][1])
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_review_can_be_resolved_by_authorized_reviewer(self):
        x=self.base(); x['checks']=(replace(x['checks'][0],status=Status.REVIEW,manual_allowed=True),x['checks'][1])
        x['resolutions']=(Resolution('c1','q1-current','reviewer-1','人工独立验算并核对题面',True),)
        self.assertTrue(evaluate_publish(**x).allowed)
    def test_stale_resolution(self):
        x=self.base(); x['checks']=(replace(x['checks'][0],status=Status.REVIEW,manual_allowed=True),x['checks'][1])
        x['resolutions']=(Resolution('c1','old-q','reviewer-1','核对旧版',True),)
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_duplicate_people_not_counted_twice(self):
        x=self.base(); x['min_content_reviewers']=3; x['content_approvals']=x['content_approvals']*3
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_three_distinct_reviewers(self):
        x=self.base(); x['min_content_reviewers']=3
        x['content_approvals']=tuple(Approval('paper-current',f'reviewer-{i}',True) for i in (1,2,3))
        self.assertTrue(evaluate_publish(**x).allowed)
    def test_author_cannot_approve_when_separation_required(self):
        x=self.base(); x['content_approvals']=(Approval('paper-current','author',True),)
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_stale_check(self):
        x=self.base(); x['checks']=(replace(x['checks'][0],subject_hash='old'),x['checks'][1])
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_missing_check(self):
        x=self.base(); x['checks']=x['checks'][1:]
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_render_not_approved(self):
        x=self.base(); x['render_approvals']=()
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_policy_blocks(self):
        x=self.base(); x['policy_allows_use']=False
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_incomplete_exam(self):
        x=self.base(); x['complete']=False
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_forged_check(self):
        x=self.base(); x['checks']=(replace(x['checks'][0],trusted=False),x['checks'][1])
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_duplicate_canonical_check(self):
        x=self.base(); x['checks']=x['checks']+(x['checks'][0],)
        self.assertFalse(evaluate_publish(**x).allowed)
    def test_non_manual_review_cannot_be_overridden(self):
        x=self.base(); x['checks']=(replace(x['checks'][0],status=Status.REVIEW,manual_allowed=False),x['checks'][1])
        x['resolutions']=(Resolution('c1','q1-current','reviewer-1','人工说明',True),)
        self.assertFalse(evaluate_publish(**x).allowed)

if __name__ == '__main__': unittest.main()
