# Calculadora de Comisiones — Renova

**Fecha:** 2026-05-18  
**Archivo afectado:** `views/profile/index.ejs`

---

## Resumen

Implementar la calculadora de comisiones del producto **Renova** en el tab "Calculadora" del perfil. Actualmente el botón Renova existe pero está deshabilitado con un mensaje de "Próximamente". Esta implementación lo activa con su lógica de comisión y la opción de traspaso.

---

## Reglas de negocio

### Comisión base
- **Solo asesor:** 10% del monto total del flipping (monto de remodelación)
- No hay comisión de gerente por ahora
- **Condición:** El asesor debe completar el proceso completo: captación, proyección, dictamen y cierre de la negociación

### Regla de traspaso
- Si el lead fue traspasado a un asesor especializado Renova:
  - **25%** de la comisión total → quien traspasó
  - **75%** de la comisión total → asesor Renova que lo trabajó
- Esta opción se activa con un toggle en la misma calculadora
- Sin traspaso: el asesor recibe el 100% de su comisión (10%)

---

## Diseño de la UI

### Inputs
1. **Monto total de la remodelación ($)** — campo de texto con formato numérico (comas)
2. **Toggle: ¿Fue traspasado a asesor especializado Renova?** — activa/desactiva la división

### Resultado sin traspaso
```
Monto de remodelación       $500,000.00
Comisión total (10%)        $50,000.00
```

### Resultado con traspaso activado
```
Comisión total (10%)        $50,000.00
💼 Quien traspasó (25%)     $12,500.00
🔨 Asesor Renova (75%)      $37,500.00
```

### Nota de advertencia (siempre visible debajo del resultado)
> ⚠️ Para recibir el 10% completo, el asesor debe realizar el proceso completo: **captación, proyección, dictamen y cierre de la negociación**.

---

## Cambios en el código

### 1. Habilitar el botón Renova
En el array de productos (línea ~245), cambiar `disabled:true` a `disabled:false` y agregar `onclick`.

### 2. Reemplazar el panel "Próximamente"
El div `#prod-renova` (línea ~451) actualmente muestra un mensaje placeholder. Se reemplaza con la calculadora completa.

### 3. Nueva función JS: `calcRenova()`
```
- Lee: r2-monto (input numérico)
- Lee: r2-traspaso (toggle boolean)
- Calcula: comision = monto * 0.10
- Si traspaso: muestra 25% / 75%
- Si no: muestra comision completa
- Oculta resultado si monto <= 0
```

### 4. Toggle de traspaso
- Elemento visual tipo pill (teal cuando activo, gris cuando inactivo)
- `onclick` llama a `calcRenova()` y actualiza estado visual
- Estado almacenado en variable JS `renovaTraspaso = false`

---

## Scope — lo que NO incluye esta iteración
- Comisión de gerente para Renova (pendiente definir)
- Regla de traspaso en otros productos (Outlet, Micro, Legal, Residencial)
- Cambios en backend / base de datos
