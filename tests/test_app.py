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

    def test_offline_matches_and_marks_missing_items(self):
        result = app.generate(self.inputs, demo=True)
        self.assertGreaterEqual(len(result['recipes']), 3)
        self.assertLessEqual(len(result['recipes']), 6)
        self.assertEqual(result['recipes'][0]['title'], 'Tomato & Basil Pasta')
        for recipe in result['recipes']:
            for item in recipe['ingredients']:
                self.assertEqual(item['missing'], item['name'] not in self.inputs['ingredients'])
        self.assertIn('[MISSING]', app.render_text(result))

    def test_demo_scales_servings(self):
        result = app.generate(app.request_input('pasta', servings=4), demo=True)
        pasta = next(r for r in result['recipes'] if r['title'] == 'Tomato & Basil Pasta')
        self.assertEqual(pasta['ingredients'][0]['quantity'], '400 g')
        self.assertTrue(all(r['servings'] == 4 for r in result['recipes']))

    def test_offline_changes_with_fridge_contents(self):
        result = app.generate(app.request_input('salmon,potatoes,spinach,butter,garlic'), demo=True)
        self.assertEqual(result['recipes'][0]['title'], 'Salmon with Buttery Potatoes & Spinach')
        self.assertNotEqual(result['recipes'][0]['title'], app.generate(self.inputs, demo=True)['recipes'][0]['title'])

    def test_offline_respects_diet_cuisine_and_time(self):
        inputs = app.request_input('zucchini,tomatoes,carrots,potatoes,onions,olive oil', dietary='vegan', cuisine='fReNcH', max_time=30)
        result = app.generate(inputs, demo=True)
        self.assertTrue(result['recipes'])
        for recipe in result['recipes']:
            self.assertLessEqual(recipe['cook_time_minutes'], 30)
            self.assertFalse({'eggs','cheese','milk','butter','cream','chicken','salmon','beef','tuna'} & {i['name'] for i in recipe['ingredients']})

    def test_rich_fridge_offers_six_different_dishes(self):
        catalog = json.loads((app.ROOT / 'examples/recipes.json').read_text())['recipes']
        names = list({item['name'] for r in catalog for item in r['ingredients']})
        result = app.generate(app.request_input(names), demo=True)
        self.assertEqual(len(result['recipes']), 6)
        self.assertEqual(len({r['title'] for r in result['recipes']}), 6)
        self.assertTrue(all(not i['missing'] for r in result['recipes'] for i in r['ingredients']))

    def test_entire_catalog_has_valid_recipes(self):
        catalog = json.loads((app.ROOT / 'examples/recipes.json').read_text())['recipes']
        for recipe in catalog:
            inputs = app.request_input([i['name'] for i in recipe['ingredients']], servings=3)
            result = app.generate(inputs, demo=True)
            match = next(r for r in result['recipes'] if r['title'] == recipe['title'])
            self.assertGreaterEqual(len(match['steps']), 3)
            self.assertTrue(all(not i['missing'] for i in match['ingredients']))

    def test_water_is_hidden_in_live_and_offline_results(self):
        fixture = json.loads(json.dumps(self.fixture))
        fixture['recipes'][0]['ingredients'].append({'name': 'tap water', 'quantity': '1 litre', 'available_name': None})
        for result in [app.validate_result(fixture, self.inputs), app.generate(self.inputs, demo=True)]:
            self.assertTrue(all(i['name'] not in ('water', 'tap water') for r in result['recipes'] for i in r['ingredients']))
        self.assertIn('water', ' '.join(app.generate(self.inputs, demo=True)['recipes'][0]['steps']))

    def test_meal_and_dish_preferences_filter_offline(self):
        cases = [
            ('eggs,tomatoes,cheese,bread,mushrooms', 'breakfast', 'main dish'),
            ('carrots,potatoes,onions', 'lunch', 'soup'),
            ('apples,bananas,yogurt,flour,milk,eggs', 'dinner', 'dessert'),
        ]
        for ingredients, meal, dish in cases:
            with self.subTest(meal=meal, dish=dish):
                result = app.generate(app.request_input(ingredients, meal_type=meal, dish_type=dish), demo=True)
                self.assertTrue(result['recipes'])
                self.assertTrue(all(meal in r['meal_types'] and r['dish_type'] == dish for r in result['recipes']))

    def test_every_meal_and_dish_option_has_offline_matches(self):
        catalog = json.loads((app.ROOT / 'examples/recipes.json').read_text())['recipes']
        names = list({i['name'] for r in catalog for i in r['ingredients']})
        for meal in app.MEAL_TYPES:
            with self.subTest(meal=meal):
                result = app.generate(app.request_input(names, meal_type=meal), demo=True)
                self.assertTrue(all(meal in r['meal_types'] for r in result['recipes']))
        for dish in app.DISH_TYPES:
            with self.subTest(dish=dish):
                result = app.generate(app.request_input(names, dish_type=dish), demo=True)
                self.assertTrue(all(r['dish_type'] == dish for r in result['recipes']))

    def test_snack_appetizer_and_brunch_sandwich_combinations(self):
        for meal, dish, ingredients in [
            ('snack', 'appetizer', 'bread,tomatoes,basil,garlic,olive oil'),
            ('brunch', 'sandwich', 'bread,cheese,tomatoes,butter,basil'),
        ]:
            with self.subTest(meal=meal, dish=dish):
                result = app.generate(app.request_input(ingredients, meal_type=meal, dish_type=dish), demo=True)
                self.assertTrue(result['recipes'])
                self.assertTrue(all(meal in r['meal_types'] and dish == r['dish_type'] for r in result['recipes']))

    def test_multiple_preferences_match_any_option_in_each_group(self):
        inputs = app.request_input('apples,sugar,cinnamon,carrots,potatoes,onions,olive oil', meal_type=['lunch', 'snack'], dish_type=['soup', 'dessert'])
        result = app.generate(inputs, demo=True)
        self.assertEqual({r['dish_type'] for r in result['recipes']}, {'soup', 'dessert'})
        self.assertTrue(all(set(inputs['meal_type']).intersection(r['meal_types']) for r in result['recipes']))
        self.assertTrue(all(r['dish_type'] in inputs['dish_type'] for r in result['recipes']))
        app.validate_result(result, inputs, expected_count=len(result['recipes']))

    def test_empty_and_duplicate_preferences(self):
        inputs = app.request_input('tomatoes', meal_type=[], dish_type=['salad', 'salad'])
        self.assertEqual(inputs['meal_type'], [])
        self.assertEqual(inputs['dish_type'], ['salad'])
        self.assertTrue(app.generate(inputs, demo=True)['recipes'])

    def test_invalid_preferences_and_ai_mismatches_rejected(self):
        for kwargs in [{'meal_type': 'midnight feast'}, {'dish_type': 'pizza'}, {'meal_type': [123]}]:
            with self.assertRaises(app.RecipeError):
                app.request_input('tomatoes', **kwargs)
        for kwargs in [{'meal_type': 'breakfast'}, {'dish_type': 'dessert'}]:
            with self.assertRaisesRegex(app.RecipeError, 'preference'):
                app.validate_result(self.fixture, app.request_input('tomatoes,pasta,basil', **kwargs))

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_ai_receives_preferences(self):
        inputs = app.request_input('tomatoes,pasta,basil', meal_type='dinner', dish_type='main dish')
        def opener(request, timeout):
            payload = json.loads(request.data)
            submitted = json.loads(payload['messages'][1]['content'])
            self.assertEqual(submitted['meal_type'], ['dinner'])
            self.assertEqual(submitted['dish_type'], ['main dish'])
            return self.response()
        result = app.generate(inputs, opener=opener)
        self.assertEqual(len(result['recipes']), 3)

    def test_combined_dietary_restrictions_are_all_applied(self):
        inputs = app.request_input('tomatoes,spinach,mushrooms,carrots,potatoes,onions,apples', dietary=['vegetarian', 'gluten-free', 'dairy-free'])
        result = app.generate(inputs, demo=True)
        catalog = {r['title']: r for r in json.loads((app.ROOT / 'examples/recipes.json').read_text())['recipes']}
        self.assertTrue(result['recipes'])
        for recipe in result['recipes']:
            self.assertTrue(set(inputs['dietary']).issubset(catalog[recipe['title']]['dietary']))

    def test_dietary_lists_normalize_and_validate(self):
        self.assertEqual(app.request_input('rice', dietary=' Vegan ')['dietary'], ['vegan'])
        self.assertEqual(app.request_input('rice', dietary=['Vegan', 'vegan', ''])['dietary'], ['vegan'])
        self.assertEqual(app.request_input('rice', dietary=[])['dietary'], [])
        for value in [None, [123], ['x' * 201]]:
            with self.assertRaises(app.RecipeError):
                app.request_input('rice', dietary=value)

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_ai_receives_all_dietary_preferences(self):
        inputs = app.request_input('tomatoes,pasta,basil', dietary=['vegetarian', 'dairy-free'])
        def opener(request, timeout):
            payload = json.loads(request.data)
            self.assertEqual(json.loads(payload['messages'][1]['content'])['dietary'], ['vegetarian', 'dairy-free'])
            self.assertIn('ALL selected dietary restrictions', payload['messages'][0]['content'])
            return self.response()
        self.assertEqual(app.generate(inputs, opener=opener)['mode'], 'live')

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

    def test_salt_and_pepper_are_available_without_selection(self):
        for name, match in [('salt', None), ('black pepper', None), ('sea salt', 'salt'), ('ground black pepper', 'pepper')]:
            with self.subTest(name=name, match=match):
                fixture = json.loads(json.dumps(self.fixture))
                fixture['recipes'][0]['ingredients'].append({'name': name, 'quantity': 'to taste', 'available_name': match})
                result = app.validate_result(fixture, self.inputs)
                seasoning = result['recipes'][0]['ingredients'][-1]
                self.assertFalse(seasoning['missing'])
                self.assertTrue(seasoning['default_available'])
                self.assertNotIn(name, self.inputs['ingredients'])
        self.assertTrue(app.validate_result(self.fixture, self.inputs)['recipes'][0]['ingredients'][3]['missing'])

    def test_unknown_fridge_match_rejected(self):
        self.fixture['recipes'][0]['ingredients'][0]['available_name'] = 'unlisted ingredient'
        with self.assertRaises(app.RecipeError): app.validate_result(self.fixture, self.inputs)

    def test_unsupported_demo_constraint_is_explicit(self):
        with self.assertRaisesRegex(app.RecipeError, 'No matching offline'):
            app.generate(app.request_input('rice', cuisine='Martian'), demo=True)

if __name__ == '__main__': unittest.main()
