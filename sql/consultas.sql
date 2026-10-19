-- 1. Solicitudes pendientes, de la más antigua a la más reciente.
SELECT s.id,
       c.nombre AS cliente,
       p.nombre AS producto,
       s.tipo,
       s.urgencia,
       s.fecha_creacion
FROM solicitudes AS s
JOIN clientes AS c ON c.id = s.cliente_id
LEFT JOIN productos AS p ON p.id = s.producto_id
WHERE s.estado = 'pendiente'
ORDER BY s.fecha_creacion ASC, s.id ASC;

-- 2. Cantidad y porcentaje de solicitudes por tipo.
SELECT tipo,
       COUNT(*) AS cantidad,
       ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM solicitudes), 0), 1) AS porcentaje
FROM solicitudes
GROUP BY tipo
ORDER BY tipo;

-- 3. Clientes con dos o más quejas, de mayor a menor.
SELECT c.nombre,
       c.ciudad,
       COUNT(*) AS numero_quejas
FROM solicitudes AS s
JOIN clientes AS c ON c.id = s.cliente_id
WHERE s.tipo = 'queja'
GROUP BY c.id, c.nombre, c.ciudad
HAVING COUNT(*) >= 2
ORDER BY numero_quejas DESC, c.nombre ASC;

-- 4. Promedio de resolución en horas por tipo; se excluyen fechas de resolución nulas.
SELECT tipo,
       ROUND(AVG((julianday(fecha_resolucion) - julianday(fecha_creacion)) * 24.0), 2) AS promedio_horas
FROM solicitudes
WHERE estado = 'resuelta'
  AND fecha_resolucion IS NOT NULL
GROUP BY tipo
ORDER BY tipo;

-- 5. Pedidos que superan el stock actual. El stock es una fotografía actual,
-- no demuestra el inventario existente al recibir cada pedido histórico.
SELECT c.nombre AS cliente,
       p.nombre AS producto,
       s.cantidad AS cantidad_pedida,
       p.stock AS stock_actual,
       s.cantidad - p.stock AS faltante
FROM solicitudes AS s
JOIN clientes AS c ON c.id = s.cliente_id
JOIN productos AS p ON p.id = s.producto_id
WHERE s.tipo = 'pedido'
  AND s.cantidad > p.stock
ORDER BY faltante DESC, s.id ASC;

-- 6. Solicitud más reciente de cada cliente (fecha descendente, id desempata).
-- Agencia Creativa Pixel (cliente 11) no tiene solicitudes; se conserva con NULL.
WITH solicitudes_ordenadas AS (
    SELECT s.*,
           ROW_NUMBER() OVER (
               PARTITION BY s.cliente_id
               ORDER BY s.fecha_creacion DESC, s.id DESC
           ) AS posicion
    FROM solicitudes AS s
)
SELECT c.id AS cliente_id,
       c.nombre AS cliente,
       r.fecha_creacion AS fecha,
       r.tipo,
       r.estado
FROM clientes AS c
LEFT JOIN solicitudes_ordenadas AS r
       ON r.cliente_id = c.id
      AND r.posicion = 1
ORDER BY c.id;
