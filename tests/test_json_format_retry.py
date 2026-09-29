"""Retry only known-completed malformed JSON; each call is separately accounted."""
import json
import unittest
from tests import live_budget_proxy_cases as cases
from tests.live_budget_proxy_shared import body


class JsonFormatRetryTests(unittest.TestCase):
    setUp = cases.BudgetProxyTests.setUp
    process = cases.BudgetProxyTests.process
    count = cases.BudgetProxyTests.count
    reservations = cases.BudgetProxyTests.reservations

    def test_one_retry_has_two_reservations_and_summed_usage(self):
        calls=[]
        def forward(payload, key):
            calls.append(json.loads(payload))
            result={'id':str(len(calls)), 'usage':{'prompt_tokens':2,'completion_tokens':3,'total_tokens':5},
                    'choices':[{'message':{'content':'{}'}}]}
            if len(calls)==1:result['_json_contract_error']='INVALID_ARGUMENT_JSON'
            return 200,json.dumps(result).encode()
        self.proxy.forward=forward
        status,response=self.process(body())
        self.assertEqual(status,200)
        self.assertEqual(len(calls),2)
        self.assertEqual(self.count(),2)
        self.assertEqual(json.loads(response)['usage']['total_tokens'],10)
        self.assertEqual(len(self.reservations()),2)

    def test_repeated_bad_json_stops_after_second_completed_attempt(self):
        calls=[]
        def forward(payload,key):
            calls.append(payload)
            return 200,b'{"_json_contract_error":"INVALID_ARGUMENT_JSON"}'
        self.proxy.forward=forward
        self.process(body())
        self.assertEqual(len(calls),2)
        self.assertEqual(self.count(),2)

    def test_unknown_network_result_is_never_retried(self):
        calls=[]
        def forward(payload,key):
            calls.append(payload)
            raise TimeoutError('no raw response')
        self.proxy.forward=forward
        self.assertEqual(self.process(body())[0],502)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.reservations()[0][1],'UNKNOWN')
