const $ = (id) => document.getElementById(id);
let ingredients = ['tomatoes', 'pasta', 'basil'];
const categories = [
  {name:'The sweet shelf', subtitle:'Fruit & baking', icon:'🍎', items:[['apples','🍎'],['bananas','🍌'],['sugar','🍬'],['cinnamon','🤎']]},
  {name:'The garden shelf', subtitle:'Vegetables & herbs', icon:'🥬', items:[['tomatoes','🍅'],['carrots','🥕'],['potatoes','🥔'],['onions','🧅'],['mushrooms','🍄'],['bell peppers','🫑'],['zucchini','🥒'],['spinach','🥬'],['basil','🌿'],['garlic','🧄']]},
  {name:'The cool shelf', subtitle:'Dairy & eggs', icon:'🧀', items:[['eggs','🥚'],['milk','🥛'],['cheese','🧀'],['butter','🧈'],['yogurt','🥣'],['cream','🥛']]},
  {name:'The hearty shelf', subtitle:'Meat, fish & plant proteins', icon:'🐟', items:[['chicken','🍗'],['beef','🥩'],['salmon','🐟'],['tuna','🐟'],['tofu','◻️'],['chickpeas','🫘']]},
  {name:'The pantry drawer', subtitle:'Grains & kitchen essentials', icon:'🍞', items:[['pasta','🍝'],['rice','🍚'],['bread','🍞'],['flour','🌾'],['olive oil','🫒'],['red wine vinegar','🍶']]}
];
const emoji = name => categories.flatMap(c => c.items).find(item => item[0] === name)?.[1] || '✦';
function toggleIngredient(name) {
  if (ingredients.includes(name)) ingredients = ingredients.filter(x => x !== name);
  else {
    if (ingredients.length >= 50) {$('error').textContent = 'You can select up to 50 ingredients.'; return;}
    ingredients.push(name);
  }
  $('error').textContent = ''; shelves();
}
function shelves() {
  const focused = document.activeElement?.dataset.ingredient;
  $('shelves').replaceChildren();
  const known = categories.flatMap(c => c.items.map(i => i[0]));
  const custom = ingredients.filter(name => !known.includes(name));
  const groups = [...categories, ...(custom.length ? [{name:'Your little extras',subtitle:'Added by you',icon:'✦',items:custom.map(name => [name,emoji(name)])}] : [])];
  groups.forEach(category => {
    const shelf = element('section', '', 'shelf');
    const heading = element('div', '', 'shelf-heading');
    heading.append(element('span', category.icon, 'shelf-icon'), element('h3', category.name), element('span', category.subtitle, 'shelf-subtitle'));
    const options = element('div', '', 'ingredient-options');
    category.items.forEach(([name, icon]) => {
      const selected = ingredients.includes(name);
      const button = element('button', '', `ingredient${selected ? ' selected' : ''}`);
      button.type = 'button'; button.dataset.ingredient = name;
      button.setAttribute('aria-pressed', String(selected));
      button.append(element('span', icon, 'food-icon'), element('span', name), element('span', selected ? '✓' : '+', 'selection-mark'));
      button.onclick = () => toggleIngredient(name); options.append(button);
    });
    shelf.append(heading,options); $('shelves').append(shelf);
  });
  $('count').textContent = `${ingredients.length} selected`;
  if (focused) [...$('shelves').querySelectorAll('button')].find(b => b.dataset.ingredient === focused)?.focus();
}
$('clear').onclick = () => {ingredients = []; shelves();};
for (const [id, delta] of [['less',-1],['more',1]]) {
  $(id).onclick = () => {$('servings').value = Math.max(1,Math.min(20,(Number($('servings').value) || 2) + delta));};
}
$('add-form').onsubmit = event => {
  event.preventDefault();
  const added = $('ingredient').value.split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
  if (added.some(x => x.length > 80) || new Set([...ingredients, ...added]).size > 50) {
    $('error').textContent = 'Use up to 50 ingredients, each under 81 characters.'; return;
  }
  ingredients = [...new Set([...ingredients, ...added])];
  $('ingredient').value = ''; $('error').textContent = ''; shelves();
};
function element(tag, text, className) {
  const node = document.createElement(tag); node.textContent = text;
  if (className) node.className = className; return node;
}
function recipes(data) {
  $('results').replaceChildren();
  data.recipes.forEach((recipe, index) => {
    const card = document.createElement('details'); card.className = 'recipe'; card.open = index === 0;
    const summary = document.createElement('summary');
    summary.append(element('span', `IDEA 0${index + 1}`, 'tag'), element('h3', recipe.title), element('span', `${recipe.cook_time_minutes} MIN  /  ${recipe.servings} SERVINGS  /  ${recipe.ingredients.filter(x => x.missing).length} MISSING`, 'meta'));
    const body = element('div', '', 'recipe-body');
    body.append(element('h4', 'The ingredients'));
    const list = document.createElement('ul');
    recipe.ingredients.forEach(item => {
      const li = document.createElement('li'); li.append(element('span', item.missing ? 'MISSING' : item.default_available ? 'PANTRY' : 'IN FRIDGE', `item-state${item.missing ? ' missing' : ''}`), document.createTextNode(`${item.quantity} ${item.name}`)); list.append(li);
    });
    body.append(list, element('h4', 'Make it happen'));
    const steps = document.createElement('ol'); recipe.steps.forEach(step => steps.append(element('li', step))); body.append(steps);
    card.append(summary, body); $('results').append(card);
  });
}
function selectedPreferences(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map(input => input.value).filter(Boolean);
}
for (const name of ['meal-type', 'dish-type', 'dietary']) {
  const options = [...document.querySelectorAll(`input[name="${name}"]`)];
  const any = options.find(input => input.value === '');
  options.forEach(input => input.addEventListener('change', () => {
    if (input === any && input.checked) options.filter(option => option !== any).forEach(option => {option.checked = false;});
    any.checked = !options.some(option => option !== any && option.checked);
  }));
}
$('recipe-form').onsubmit = async event => {
  event.preventDefault(); $('error').textContent = '';
  if (!ingredients.length) {$('error').textContent = 'Add at least one ingredient to your fridge.'; return;}
  $('generate').disabled = true; $('results').setAttribute('aria-busy', 'true');
  $('results').replaceChildren(); $('status').textContent = 'Looking for your next favourite meal…';
  try {
    const response = await fetch('/api/recipes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ingredients, meal_type:selectedPreferences('meal-type'), dish_type:selectedPreferences('dish-type'), dietary:selectedPreferences('dietary'), cuisine:$('cuisine').value, max_time:document.querySelector('input[name="max-time"]:checked').value ? Number(document.querySelector('input[name="max-time"]:checked').value) : null, servings:$('servings').value ? Number($('servings').value) : null})});
    const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Recipe request failed.');
    recipes(data); $('status').textContent = data.mode === 'demo' ? `${data.recipes.length} matching recipes from our ${data.catalog_size}-dish collection — no API needed.` : 'Three fresh possibilities. Pick one and make it yours.';
  } catch (error) {$('error').textContent = error.message; $('status').textContent = 'Adjust your ingredients or constraints and try again.';}
  finally {$('generate').disabled = false; $('results').removeAttribute('aria-busy');}
};
fetch('/api/config').then(r => r.json()).then(data => {$('mode').textContent = data.mode === 'demo' ? 'OFFLINE KITCHEN' : 'AI KITCHEN'; $('demo-note').hidden = data.mode !== 'demo';}).catch(() => {$('mode').textContent = 'SERVER UNAVAILABLE';});
shelves();
