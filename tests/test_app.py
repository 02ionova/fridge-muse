import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import app

class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.inputs = app.request_input('tomatoes,pasta,basil', max_time=20, servings=2)
        self.fixture = json.loads((app.ROOT / 'examples/demo.json').read_text())
        for r in self.fixture['recipes']:
            for i in r['ingredients']:
                i['quantity'] = '1 portion'
                i['available_name'] = i['name'] if i['name'] in self.inputs['ingredients'] else None

    def response(self):
        return io.BytesIO(json.dumps({'choices': [{'message': {'content': json.dumps(self.fixture)}}]}).encode())

    def test_demo_has_three_complete_recipes_and_missing_items(self):
        result = app.generate(self.inputs, demo=True)
        self.assertEqual(len(result['recipes']), 3)
        self.assertFalse(result['recipes'][0]['ingredients'][0]['missing'])
        self.assertTrue(result['recipes'][0]['ingredients'][3]['missing'])
        self.assertIn('[MISSING]', app.render_text(result))

    def test_demo_scales_servings(self):
        result = app.generate(app.request_input('pasta', servings=4), demo=True)
        self.assertEqual(result['recipes'][0]['ingredients'][0]['quantity'], '400 g')
        self.assertEqual(result['recipes'][0]['servings'], 4)

    def test_input_validation(self):
        for kwargs in ({'ingredients': ''}, {'ingredients': ['x'], 'servings': 0}, {'ingredients': ['x'], 'max_time': True}, {'ingredients': [123]}):
            with self.assertRaises(app.RecipeError): app.request_input(**kwargs)

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_transient_http_failure_retries_then_succeeds(self):
        calls, delays = [], []
        def opener(request, timeout):
            calls.append(request)
            if len(calls) == 1: raise HTTPError(request.full_url, 429, 'rate limit', {}, None)
            return self.response()
        result = app.generate(self.inputs, opener=opener, sleeper=delays.append)
        self.assertEqual(result['mode'], 'live')
        self.assertEqual(len(calls), 2)
        self.assertEqual(delays, [1])
        payload = json.loads(calls[0].data)
        self.assertTrue(payload['response_format']['json_schema']['strict'])

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_network_failures_stop_after_three_attempts(self):
        calls = []
        def opener(*args, **kwargs):
            calls.append(1); raise URLError('offline')
        with self.assertRaisesRegex(app.RecipeError, 'three attempts'):
            app.generate(self.inputs, opener=opener, sleeper=lambda _: None)
        self.assertEqual(len(calls), 3)

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_auth_error_not_retried(self):
        calls = []
        def opener(request, timeout):
            calls.append(1); raise HTTPError(request.full_url, 401, 'unauthorized', {}, None)
        with self.assertRaisesRegex(app.RecipeError, 'authentication'):
            app.generate(self.inputs, opener=opener, sleeper=lambda _: self.fail('Should not retry'))
        self.assertEqual(len(calls), 1)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key(self):
        with self.assertRaisesRegex(app.RecipeError, 'OPENAI_API_KEY'):
            app.generate(self.inputs)

    def test_wrong_recipe_count_rejected(self):
        self.fixture['recipes'].pop()
        with self.assertRaises(app.RecipeError): app.validate_result(self.fixture, self.inputs)

    def test_constraint_violation_rejected(self):
        self.fixture['recipes'][0]['cook_time_minutes'] = 30
        with self.assertRaisesRegex(app.RecipeError, 'time budget'):
            app.validate_result(self.fixture, self.inputs)

    def test_unknown_fridge_match_rejected(self):
        self.fixture['recipes'][0]['ingredients'][0]['available_name'] = 'unlisted ingredient'
        with self.assertRaises(app.RecipeError): app.validate_result(self.fixture, self.inputs)

    def test_unsupported_demo_constraint_is_explicit(self):
        with self.assertRaisesRegex(app.RecipeError, 'Demo supports'):
            app.generate(app.request_input('rice', dietary='vegan'), demo=True)

if __name__ == '__main__': unittest.main()
