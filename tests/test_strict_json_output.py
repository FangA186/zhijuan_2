import json
import unittest
from unittest.mock import patch
from tools.deepseek_json_contract import prepare_strict_request, unwrap_strict_response, FUNCTION_NAME
from tools.live_budget_proxy import forward_upstream


class StrictJsonOutputTests(unittest.TestCase):
    def test_provider_request_is_strict_and_response_is_only_unwrapped(self):
        candidate = {'public': {'kind': 'multiple_choice'}, 'private': {'answers': []}}
        response = {'usage': {'total_tokens': 12}, 'choices': [{'finish_reason': 'tool_calls',
                    'message': {'tool_calls': [{'function': {'name': FUNCTION_NAME,
                                 'arguments': json.dumps(candidate)}}]}}]}
        class Reply:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(response).encode()
        with patch('tools.live_budget_proxy.urllib.request.urlopen', return_value=Reply()) as send:
            status, result = forward_upstream(json.dumps({'model':'deepseek-flash','messages':[],
                                                         'response_format':{'type':'json_object'}}).encode(), 'test')
        request = send.call_args.args[0]
        body = json.loads(request.data)
        self.assertIn('/beta/chat/completions', request.full_url)
        self.assertTrue(body['tools'][0]['function']['strict'])
        self.assertNotIn('response_format', body)
        self.assertEqual(status, 200)
        result = json.loads(result)
        self.assertEqual(json.loads(result['choices'][0]['message']['content']), candidate)
        self.assertEqual(result['usage']['total_tokens'], 12)
        self.assertNotIn('tool_calls', result['choices'][0]['message'])

    def test_invalid_or_truncated_output_never_becomes_success(self):
        for reason, name, arguments in [('length',FUNCTION_NAME,'{"result":{}}'),
                                        ('tool_calls','other','{"result":{}}'),
                                        ('tool_calls',FUNCTION_NAME,'broken')]:
            envelope={'choices':[{'finish_reason':reason,'message':{'tool_calls':[{
                'function':{'name':name,'arguments':arguments}}]}}]}
            result=json.loads(unwrap_strict_response(json.dumps(envelope).encode()))
            self.assertEqual(result['choices'][0]['message']['content'],'')

    def test_schema_is_closed_and_call_has_no_executable_tool(self):
        body=prepare_strict_request({'messages':[],'stop':['}']})
        self.assertNotIn('stop',body)
        self.assertEqual(body['tool_choice']['function']['name'],FUNCTION_NAME)
        def visit(node):
            if isinstance(node,dict):
                if node.get('type')=='object':
                    self.assertFalse(node['additionalProperties'])
                    self.assertEqual(set(node['required']),set(node['properties']))
                for value in node.values():visit(value)
            elif isinstance(node,list):
                for value in node:visit(value)
        visit(body['tools'][0]['function']['parameters'])
        author = prepare_strict_request({'messages':[{'role':'system','content':'Role: author.'}]})
        schema = author['tools'][0]['function']['parameters']
        self.assertEqual(set(schema['properties']), {'public','private'})
        visit(schema)
