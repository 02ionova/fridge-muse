const $ = (id) => document.getElementById(id);
let ingredients = ['tomatoes', 'pasta', 'basil'];
const emoji = (name) => ({tomatoes:'🍅', pasta:'🍝', basil:'🌿', eggs:'🥚', milk:'🥛', cheese:'🧀', bread:'🍞', rice:'🍚', chicken:'🍗', carrots:'🥕', potatoes:'🥔', mushrooms:'🍄'}[name] || '✳');
function shelves() {
  $('shelves').replaceChildren();
  ingredients.forEach(name => {
    const button = document.createElement('button');
    button.className = 'ingredient'; button.type = 'button';
    button.textContent = `${emoji(name)} ${name} ×`;
    button.setAttribute('aria-label', `Remove ${name}`);
    button.onclick = () => {ingredients = ingredients.filter(x => x !== name); shelves();};
    $('shelves').append(button);
  });
  $('count').textContent = `${ingredients.length} ingredients`;
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
      const li = document.createElement('li'); li.append(element('span', item.missing ? 'MISSING' : 'IN FRIDGE', `item-state${item.missing ? ' missing' : ''}`), document.createTextNode(`${item.quantity} ${item.name}`)); list.append(li);
    });
    body.append(list, element('h4', 'Make it happen'));
    const steps = document.createElement('ol'); recipe.steps.forEach(step => steps.append(element('li', step))); body.append(steps);
    card.append(summary, body); $('results').append(card);
  });
}
$('recipe-form').onsubmit = async event => {
  event.preventDefault(); $('error').textContent = '';
  if (!ingredients.length) {$('error').textContent = 'Add at least one ingredient to your fridge.'; return;}
  $('generate').disabled = true; $('results').setAttribute('aria-busy', 'true');
  $('results').replaceChildren(); $('status').textContent = 'Looking for your next favourite meal…';
  try {
    const response = await fetch('/api/recipes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ingredients, dietary:$('dietary').value, cuisine:$('cuisine').value, max_time:$('max-time').value ? Number($('max-time').value) : null, servings:$('servings').value ? Number($('servings').value) : null})});
    const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Recipe request failed.');
    recipes(data); $('status').textContent = data.mode === 'demo' ? 'Three fixed demo recipes — no API was called.' : 'Three fresh possibilities. Pick one and make it yours.';
  } catch (error) {$('error').textContent = error.message; $('status').textContent = 'Adjust your ingredients or constraints and try again.';}
  finally {$('generate').disabled = false; $('results').removeAttribute('aria-busy');}
};
fetch('/api/config').then(r => r.json()).then(data => {$('mode').textContent = data.mode === 'demo' ? 'OFFLINE DEMO' : 'AI KITCHEN';}).catch(() => {$('mode').textContent = 'SERVER UNAVAILABLE';});
shelves();
