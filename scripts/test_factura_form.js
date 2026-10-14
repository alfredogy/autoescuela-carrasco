const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function formulario() {
    class Element {
        constructor(value = '') {
            this.value = value;
            this.children = [];
            this.events = {};
            this.dataset = {url: '/api/buscar-alumno/'};
            this.classList = {toggle() {}};
        }
        set innerHTML(value) { throw new Error('Unsafe rendering: ' + value); }
        addEventListener(type, callback) { this.events[type] = callback; }
        replaceChildren() { this.children = []; this.textContent = ''; }
        appendChild(child) { this.children.push(child); }
        input(value) { this.value = value; this.events.input({target: this}); }
    }
    const ids = ['id_total_pagado', 'id_tasa_basica', 'id_tasa_a', 'id_traslado', 'id_renovaciones',
        'id_curso', 'id_tasa_tacografo', 'tasas-conduccion', 'tasa-tacografo', 'preview-error',
        'preview-base', 'preview-iva', 'preview-tasas', 'preview-total', 'alumno-search',
        'alumno-results', 'id_alumno_id', 'id_nombre_factura', 'id_dni_factura',
        'id_direccion_factura', 'id_cp_factura', 'id_municipio_factura', 'id_provincia_factura'];
    const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
    elements.id_curso.value = 'B';
    elements.id_alumno_id.value = '1';
    elements.id_nombre_factura.value = 'Snapshot original';
    elements.id_direccion_factura.value = 'Direccion personalizada';
    const timers = new Map();
    const requests = [];
    let timerId = 0;
    let ready;
    vm.runInNewContext(readFileSync(path.join(__dirname, '../static/js/factura_form.js'), 'utf8'), {
        document: {getElementById: id => elements[id], createElement: () => new Element(),
            addEventListener: (type, callback) => { ready = callback; }},
        setTimeout: callback => { timers.set(++timerId, callback); return timerId; },
        clearTimeout: id => timers.delete(id),
        AbortController, URLSearchParams,
        fetch: (url, options) => new Promise(resolve => requests.push({url, options, resolve})),
    });
    ready();
    return {elements, requests, runTimers() {
        const callbacks = [...timers.values()];
        timers.clear();
        callbacks.forEach(callback => callback());
    }};
}

const alumno = {id: 27, nombre: '<img src=x onerror=alert(1)> GAO', dni: '',
    direccion: 'Calle alumno', cp: '46470', municipio: 'Albal', provincia: 'VALENCIA'};

async function respuesta(request, results) {
    request.resolve({json: async () => ({found: !!results.length, results})});
    await new Promise(resolve => setImmediate(resolve));
}

test('Search does not overwrite snapshots; explicit selection safely fills and links', async () => {
    const f = formulario();
    f.elements['alumno-search'].input('ALFREDO GAO');
    f.runTimers();
    await respuesta(f.requests[0], [alumno]);
    assert.equal(f.elements.id_alumno_id.value, '');
    assert.equal(f.elements.id_nombre_factura.value, 'Snapshot original');
    assert.equal(f.elements.id_direccion_factura.value, 'Direccion personalizada');
    const button = f.elements['alumno-results'].children[0];
    assert.equal(button.type, 'button');
    assert.equal(button.textContent, alumno.nombre + ' (Sin DNI) #27');
    button.events.click();
    assert.equal(f.elements.id_alumno_id.value, 27);
    assert.equal(f.elements.id_nombre_factura.value, alumno.nombre);
    assert.equal(f.elements.id_dni_factura.value, '');
    assert.equal(f.elements.id_direccion_factura.value, alumno.direccion);
    assert.equal(f.elements['alumno-results'].children.length, 0);
});

test('Search, invoice name and DNI changes each clear stale selected IDs', () => {
    const f = formulario();
    for (const id of ['alumno-search', 'id_nombre_factura', 'id_dni_factura']) {
        f.elements.id_alumno_id.value = '27';
        f.elements[id].input('Otro alumno');
        assert.equal(f.elements.id_alumno_id.value, '');
    }
});

test('Out of order responses cannot replace latest results', async () => {
    const f = formulario();
    f.elements['alumno-search'].input('primero');
    f.runTimers();
    f.elements['alumno-search'].input('segundo');
    assert.equal(f.requests[0].options.signal.aborted, true);
    f.runTimers();
    await respuesta(f.requests[1], [{...alumno, id: 28, nombre: 'Segundo'}]);
    await respuesta(f.requests[0], [alumno]);
    assert.equal(f.elements['alumno-results'].children.length, 1);
    assert.equal(f.elements['alumno-results'].children[0].textContent, 'Segundo (Sin DNI) #28');
});

test('Clearing input clears results and ignores an outstanding search', async () => {
    const f = formulario();
    f.elements['alumno-search'].input('ALFREDO');
    f.runTimers();
    f.elements['alumno-search'].input('');
    await respuesta(f.requests[0], [alumno]);
    assert.equal(f.elements.id_alumno_id.value, '');
    assert.equal(f.elements['alumno-results'].children.length, 0);
    assert.equal(f.elements.id_nombre_factura.value, 'Snapshot original');
});

test('DNI lookup uses the same selectable list, not automatic first selection', async () => {
    const f = formulario();
    f.elements.id_dni_factura.input('12345678Z');
    f.runTimers();
    assert.match(f.requests[0].url, /q=12345678Z$/);
    await respuesta(f.requests[0], [alumno, {...alumno, id: 28}]);
    assert.equal(f.elements['alumno-results'].children.length, 2);
    assert.equal(f.elements.id_alumno_id.value, '');
    assert.equal(f.elements.id_nombre_factura.value, 'Snapshot original');
});
