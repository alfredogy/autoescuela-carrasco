// Cálculo en tiempo real para el formulario de facturas
(function() {
    'use strict';

    const fields = ['id_total_pagado', 'id_tasa_basica', 'id_tasa_a', 'id_traslado', 'id_renovaciones', 'id_curso'];

    function calcular() {
        const totalPagado = parseFloat(document.getElementById('id_total_pagado')?.value) || 0;
        const tasaBasica = document.getElementById('id_tasa_basica')?.checked ? 1 : 0;
        const tasaA = document.getElementById('id_tasa_a')?.checked ? 1 : 0;
        const traslado = document.getElementById('id_traslado')?.checked ? 1 : 0;
        const renovaciones = parseInt(document.getElementById('id_renovaciones')?.value) || 0;
        const curso = document.getElementById('id_curso')?.value || 'B';

        if (totalPagado <= 0) {
            updatePreview('0.00', '0.00', '0.00', '0.00');
            return;
        }

        const params = new URLSearchParams({
            total_pagado: totalPagado,
            tasa_basica: tasaBasica,
            tasa_a: tasaA,
            traslado: traslado,
            renovaciones: renovaciones,
            curso: curso
        });

        fetch('/api/calcular/?' + params.toString())
            .then(r => r.json())
            .then(data => {
                if (data.error) return;
                updatePreview(data.base, data.iva, data.tasas, data.total);
            })
            .catch(() => {});
    }

    function updatePreview(base, iva, tasas, total) {
        document.getElementById('preview-base').textContent = parseFloat(base).toFixed(2) + ' \u20ac';
        document.getElementById('preview-iva').textContent = parseFloat(iva).toFixed(2) + ' \u20ac';
        document.getElementById('preview-tasas').textContent = parseFloat(tasas).toFixed(2) + ' \u20ac';
        document.getElementById('preview-total').textContent = parseFloat(total).toFixed(2) + ' \u20ac';
    }

    // Búsqueda de alumno por DNI
    let searchTimeout = null;
    function buscarAlumno() {
        const dni = document.getElementById('id_dni_factura')?.value || '';
        if (dni.length < 3) return;

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            fetch('/api/buscar-alumno/?dni=' + encodeURIComponent(dni))
                .then(r => r.json())
                .then(data => {
                    if (data.found) {
                        const nombreField = document.getElementById('id_nombre_factura');
                        const dirField = document.getElementById('id_direccion_factura');
                        const cpField = document.getElementById('id_cp_factura');
                        const munField = document.getElementById('id_municipio_factura');
                        const provField = document.getElementById('id_provincia_factura');

                        if (nombreField && !nombreField.value) nombreField.value = data.nombre;
                        if (dirField && !dirField.value) dirField.value = data.direccion;
                        if (cpField && !cpField.value) cpField.value = data.cp;
                        if (munField && !munField.value) munField.value = data.municipio;
                        if (provField && !provField.value) provField.value = data.provincia;
                    }
                })
                .catch(() => {});
        }, 500);
    }

    // Event listeners
    document.addEventListener('DOMContentLoaded', function() {
        fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', calcular);
                el.addEventListener('input', calcular);
            }
        });

        const dniField = document.getElementById('id_dni_factura');
        if (dniField) {
            dniField.addEventListener('input', buscarAlumno);
        }

        // Calcular al cargar (para edición)
        calcular();
    });
})();
