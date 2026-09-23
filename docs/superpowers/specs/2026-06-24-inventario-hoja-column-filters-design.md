# Spec: Filtros tipo Excel en columnas de inventario-hoja.ejs

**Fecha:** 2026-06-24
**Estado:** Aprobado

---

## Resumen

Agregar dropdowns de filtro tipo Excel en cada encabezado de la tabla `inventario-hoja.ejs`. Al hacer clic en cualquier columna del header, aparece un dropdown con checkboxes (columnas de texto) o rangos mín/máx (columnas numéricas). Los filtros se combinan con los filtros del toolbar y drawer que ya existen.

---

## Tipos de dropdown

### Columnas de categoría / texto
Aplica a: **Lista, Etapa, Tipo, Estatus, Calle, Colonia, Municipio, Estado, C.P., Alrededores, Expte.**

Contenido del dropdown:
- Campo de búsqueda interno (siempre visible — útil para columnas con muchos valores como Calle o Colonia)
- Opción "(Todos)" con checkbox — marca/desmarca todos
- Lista de checkboxes con los valores únicos extraídos automáticamente de las filas del DOM (`data-*` atributos)
- Botón **OK** (aplica filtro y cierra) y **Limpiar** (quita filtro de esa columna)

### Columnas numéricas
Aplica a: **Terreno m², Constr. m², Rec., Baños, Est., Costo cesión, Honorarios, Costo total, Valor comercial**

Contenido del dropdown:
- Dos inputs: **Mínimo** y **Máximo** (tipo `number`)
- Botón **OK** y **Limpiar**

### Columna excluida
- `#` (numeración de fila) — sin filtro

---

## Estado visual del header activo

Cuando una columna tiene filtro activo:
- El texto del header cambia a color teal (`#52BEC0`)
- Aparece un badge circular teal con el número de valores seleccionados (categoría) o `"1"` (numérico con rango activo)
- Al limpiar el filtro, el header vuelve al color original

---

## Comportamiento

- Click en header → abre el dropdown de esa columna; cierra cualquier otro dropdown abierto
- Click fuera del dropdown o tecla `Escape` → cierra el dropdown activo
- El filtrado es **inmediato** al hacer click en OK (no requiere recarga de página)
- Los filtros de columna se **combinan** con los filtros ya existentes del toolbar (búsqueda, Estado, Municipio, Colonia, Lista) y del drawer avanzado — todos aplican al mismo tiempo a través de la función `matches()`
- Las columnas de categoría permiten **selección múltiple** (checkboxes)
- El dropdown sigue la columna aunque la tabla haga scroll horizontal

---

## Arquitectura técnica

### Sin cambios al servidor
Todo es JavaScript en el cliente dentro del mismo archivo `views/pages/inventario-hoja.ejs`. No se modifica ningún controlador ni ruta.

### Mapa columna → data-attribute

| Header | Tipo | data-attribute |
|---|---|---|
| Lista | categoría | `data-lista` |
| Etapa | categoría | `data-etapa` (agregar al `<tr>`) |
| Tipo | categoría | `data-tipo` |
| Estatus | categoría | `data-estatus` |
| Calle | categoría | `data-calle` |
| Colonia | categoría | `data-colonia` |
| Municipio | categoría | `data-municipio` |
| Estado | categoría | `data-estado` |
| C.P. | categoría | `data-cp` |
| Alrededores | categoría | `data-alred` (agregar al `<tr>`) |
| Expte. | categoría | `data-expte` (agregar al `<tr>`) |
| Terreno m² | numérico | `data-terreno` |
| Constr. m² | numérico | `data-construccion` |
| Rec. | numérico | `data-rec` |
| Baños | numérico | `data-san` |
| Est. | numérico | `data-est` |
| Costo cesión | numérico | `data-costo-cesion` |
| Honorarios | numérico | `data-honorarios` |
| Costo total | numérico | `data-costo-total` |
| Valor comercial | numérico | `data-valor-com` |

> Nota: Las columnas `Etapa`, `Alrededores` y `Expte.` ya tienen el valor en el EJS pero no en el `data-*` del `<tr>`. Se agrega `data-etapa`, `data-alred` y `data-expte` al atributo del `<tr>`.

### Estado de filtros activos
```javascript
// Objeto global de filtros de columna
const colFilters = {
  // categoría: { values: Set de valores seleccionados, type: 'cat' }
  // numérico:  { min: number|null, max: number|null, type: 'num' }
};
```

### Integración con matches()
Se extiende la función `matches(el)` existente con una sección al final que itera `colFilters` y verifica cada filtro activo contra los `data-*` del elemento.

### CSS del dropdown
Estilos inline dentro del bloque `<style>` ya existente:
- `.col-drop` — el dropdown (position: absolute, z-index: 99, fondo blanco, sombra, border-radius 10px)
- `.col-drop-item` — cada opción checkbox
- `.col-th-badge` — el badge contador teal
- `.col-th-active` — clase aplicada al `<th>` con filtro activo (cambia color a teal)
- Dropdown se posiciona relativo al `<th>` con `position: relative`

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `views/pages/inventario-hoja.ejs` | Agregar `data-etapa`, `data-alred`, `data-expte` al `<tr>`; agregar CSS del dropdown; reemplazar `<th>` con wrappers clickables; agregar JS de dropdowns e integración con `matches()` |

Solo **un archivo** se modifica.

---

## Fuera de alcance

- Persistencia de filtros al recargar la página (sessionStorage/localStorage)
- Columna Costo compra y Ganancia (solo visibles cuando `showInternal` es true — se incluyen si están visibles)
- Columna Ubicación (es un link — sin valor filtrable significativo)
- Ordenamiento (sort) por columna al hacer clic en el header
