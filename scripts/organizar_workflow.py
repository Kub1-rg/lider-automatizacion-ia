"""Distribuye el workflow para sustentación; solo cambia posiciones y notas."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'flujo/solicitudes.json'


def arrange(workflow):
    workflow = copy.deepcopy(workflow)
    workflow['nodes'] = [node for node in workflow['nodes']
                         if not node['id'].startswith('layout-')]
    result = copy.deepcopy(workflow)
    nodes = {node['name']: node for node in result['nodes']}
    placed = set()

    def lane(names, x, y):
        for index, name in enumerate(names):
            assert name not in placed, name
            nodes[name]['position'] = [x + index * 300, y]
            placed.add(name)

    def note(key, title, content, x, y, width, height, color):
        result['nodes'].append({
            'id': 'layout-' + key, 'name': title,
            'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1,
            'position': [x, y],
            'parameters': {'content': '## ' + title + '\n\n' + content,
                           'width': width, 'height': height, 'color': color},
        })

    lane(['Webhook solicitud', 'Validar entrada', 'Entrada válida',
          'Contexto HTTP 01', 'Persistir recepción',
          'Recuperar entrada después de recepción', 'Leer recepción',
          'Recepción disponible', 'Es repetición terminal'], 0, 0)
    lane(['Responder entrada inválida'], 600, 260)
    lane(['Responder API no disponible'], 2100, 260)
    lane(['Normalizar resultado previo', 'Responder recepción existente'], 2400, -300)
    note('entrada', '01 · Recepción e idempotencia',
         'INICIO → validar → conservar recepción → detectar repetición.\n'
         'Entrada inválida: 422. Recepción no disponible: 503. Una repetición terminal devuelve el resultado guardado.\n'
         '**Si es nueva, continúa en 02 ↓**', -100, -550, 2950, 1000, 5)

    lane(['Contexto HTTP 11', 'Marcar recepción procesando',
          'Recuperar contexto procesando', 'Contexto HTTP 02',
          'Consultar cliente', 'Recuperar contexto cliente',
          'Contexto HTTP 03', 'Consultar catálogo',
          'Recuperar contexto catálogo', 'Preparar petición LLM'], 0, 800)
    lane(['API catálogo disponible', 'Clave DeepSeek configurada'], 2700, 1080)
    note('contexto', '02 · Contexto desde la API',
         'Marcar en proceso → consultar cliente → consultar catálogo → preparar el mensaje.\n'
         'Los nodos «Contexto HTTP» y «Recuperar» preservan los datos entre llamadas HTTP.\n'
         '**API y clave disponibles: continúa en 03 ↓. Fallos: bloque 08.**', -100, 530, 3250, 770, 4)

    lane(['Contexto HTTP 04', 'DeepSeek extracción intento 1',
          'Recuperar contexto LLM 1', 'Validar respuesta intento 1',
          'Contexto HTTP 12', 'Guardar extracción intento 1',
          'Recuperar extracción primer intento', 'JSON válido intento 1'], 0, 1600)
    note('llm', '03 · Clasificación con IA',
         'DeepSeek extrae JSON → validar contrato → guardar extracción.\n'
         '**JSON válido: 04 ↓. JSON inválido: 05 →.**\n'
         'El modelo clasifica; la API mantiene las reglas de negocio y la persistencia.', -100, 1330, 3250, 560, 6)

    lane(['Resolver cliente y producto', 'Datos registrables',
          'Contexto HTTP 05', 'Crear solicitud', 'Recuperar solicitud creada',
          'Hay alerta para notificar', 'Contexto HTTP 06',
          'Enviar alerta por API', 'Recuperar resultado de alerta',
          'Responder solicitud creada'], 0, 2200)
    note('registro', '04 · Registro y alertas · ruta principal',
         'Resolver referencias → registrar solicitud → evaluar alerta → responder 201.\n'
         'B1: urgencia · B2: consulta · B3: queja · B4: stock insuficiente.\n'
         '**Datos insuficientes o cliente desconocido: 07.** La API controla el envío de correo.', -100, 1930, 3250, 560, 3)

    lane(['Reintento permitido', 'Contexto HTTP 08',
          'DeepSeek corrección intento 2', 'Recuperar contexto LLM 2',
          'Validar respuesta intento 2', 'Contexto HTTP 13',
          'Guardar extracción intento 2', 'Recuperar extracción segundo intento',
          'JSON válido intento 2'], 3600, 1600)
    note('reintento', '05 · Corrección · solo si hace falta',
         'Ruta excepcional: un segundo intento cuando está permitido.\n'
         '**Corrección válida: 06 ↓. Sin reintento o salida inválida: 07 ↓.**\n'
         'Esta ruta no se ejecuta cuando el primer intento ya es válido.', 3500, 1330, 2950, 560, 2)

    lane(['Resolver tras reintento', 'Datos registrables tras reintento',
          'Contexto HTTP 09', 'Crear solicitud tras reintento',
          'Recuperar solicitud reintentada', 'Hay alerta tras reintento',
          'Contexto HTTP 10', 'Enviar alerta reintento',
          'Recuperar alerta reintentada', 'Responder solicitud reintentada'], 3600, 2200)
    note('registro-reintento', '06 · Registro después de corregir',
         'Mismas reglas de registro y alertas de la ruta principal, después del segundo intento.\n'
         '**Datos registrables: responder 201. Datos insuficientes: 07 ↓.**', 3500, 1930, 3250, 560, 3)

    lane(['Contexto HTTP 07', 'Guardar revisión manual',
          'Recuperar revisión guardada', 'Responder revisión manual'], 3600, 2900)
    note('revision', '07 · Revisión humana · salida controlada',
         'B5: cliente desconocido → conservar recepción → revisión manual → responder 202.\n'
         'También recibe salidas no utilizables del proveedor. **No inventa cliente ni crea una solicitud inválida.**', 3500, 2630, 1750, 560, 2)

    lane(['Marcar proveedor no configurado'], 2700, 2900)
    lane(['Preparar error API controlado', 'Responder API de búsqueda no disponible'], 1200, 2900)
    note('errores', '08 · Configuración y fallos de API',
         'API no disponible: respuesta 503 controlada.\n'
         'Proveedor sin clave: conservar el motivo y continuar a revisión manual (07).', 1100, 2630, 2050, 560, 7)
    note('guia', 'GUÍA PARA SUSTENTAR · Solicitudes con IA',
         '**Ruta principal:** 01 ↓ 02 ↓ 03 ↓ 04.\n'
         '**Excepciones:** 05 → 06 (corrección), 07 (revisión humana), 08 (fallos).\n\n'
         'Lee cada bloque de izquierda a derecha. Acerca el zoom al bloque que estás explicando.\n'
         '69 nodos funcionales originales. Las notas y posiciones solo organizan la presentación.\n'
         'No se descuenta inventario ni se confirma una entrega.', 3500, -550, 1750, 650, 5)

    assert placed == set(nodes), set(nodes) - placed
    assert result['connections'] == workflow['connections']
    for old, new in zip(workflow['nodes'], result['nodes']):
        assert {k: v for k, v in old.items() if k != 'position'} == {
            k: v for k, v in new.items() if k != 'position'}
    return result


if __name__ == '__main__':
    raw = PATH.read_bytes()
    newline = '\r\n' if b'\r\n' in raw else '\n'
    original = json.loads(raw)
    updated = arrange(original)
    PATH.write_bytes((json.dumps(updated, ensure_ascii=False, indent=2) + '\n').replace('\n', newline).encode('utf-8'))
    print('Layout actualizado: 69 nodos funcionales preservados; 9 notas; conexiones idénticas.')
