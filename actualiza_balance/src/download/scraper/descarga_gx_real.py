"""
descarga_gx_real.py
"""

import asyncio
import csv
import json
import argparse
from pathlib import Path

import websockets

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

HOST      = "qap-prd.coordinador.cl"
APP_ID    = "6b071a6f-8cac-443a-84e4-c4617babf102"
OBJECT_ID = "22dae709-3f9f-407f-be47-450c68775530"

WS_URL = (
    f"wss://{HOST}/ext/app/{APP_ID}"
    f"?reloadUri=https%3A%2F%2F{HOST}%2Fext%2Fextensions%2F"
    f"mashup_Generacion_Real_Descargable%2Fmashup_Generacion_Real_Descargable.html"
)

COOKIES: dict[str, str] = {}
CHUNK_SIZE   = 300
MAX_PARALLEL = 10

# ==============================================================================
# DISPATCHER
# ==============================================================================

class QlikWS:
    def __init__(self, ws):
        self.ws = ws
        self._waiters: dict[int, asyncio.Future] = {}
        self._task = None

    def start(self):
        self._task = asyncio.ensure_future(self._dispatch())

    async def _dispatch(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                mid = msg.get("id")
                if mid in self._waiters:
                    fut = self._waiters.pop(mid)
                    if not fut.done():
                        fut.set_result(msg)
        except Exception:
            for fut in self._waiters.values():
                if not fut.done():
                    fut.set_exception(ConnectionError("WebSocket cerrado"))

    async def send_recv(self, payload: dict) -> dict:
        mid = payload["id"]
        fut = asyncio.get_event_loop().create_future()
        self._waiters[mid] = fut
        await self.ws.send(json.dumps(payload))
        return await fut

    def stop(self):
        if self._task:
            self._task.cancel()

# ==============================================================================
# HELPERS JSON-RPC
# ==============================================================================

def rpc(method, params, id):
    return {"jsonrpc": "2.0", "id": id, "method": method, "params": params, "handle": -1}

def rpc_handle(handle, method, params, id):
    return {"jsonrpc": "2.0", "id": id, "method": method, "params": params, "handle": handle}

# ==============================================================================
# FILTROS
# ==============================================================================

async def aplicar_filtro(qws, app_handle, field_name, value, id):
    resp = await qws.send_recv(rpc_handle(app_handle, "GetField", [field_name], id=id))
    field_handle = resp["result"]["qReturn"]["qHandle"]
    await qws.send_recv(rpc_handle(field_handle, "Select", [str(value)], id=id + 1))
    return id + 2

# ==============================================================================
# DESCARGA PRINCIPAL
# ==============================================================================

async def descargar(anio: int, mes: int, carpeta: Path):
    carpeta.mkdir(parents=True, exist_ok=True)
    headers = {"Origin": f"https://{HOST}"}
    if COOKIES:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in COOKIES.items())

    print(f"🔌 Conectando... (año={anio}, mes={mes})")

    ws_kwargs = dict(
        additional_headers=headers,
        max_size=100 * 1024 * 1024,
        ping_interval=60,
        ping_timeout=120,
        open_timeout=30,
        close_timeout=10,
    )

    # --- Primera conexión: obtener layout ---
    total_rows = 0
    total_cols = 0
    headers_row = []

    async with websockets.connect(WS_URL, **ws_kwargs) as ws:
        qws = QlikWS(ws)
        qws.start()
        try:
            print("📂 Abriendo app...")
            resp = await qws.send_recv(rpc("OpenDoc", [APP_ID, "", "", "", False], id=1))
            app_handle = resp["result"]["qReturn"]["qHandle"]

            print(f"🔍 Aplicando filtros: Año={anio}, Mes={mes}...")
            next_id = await aplicar_filtro(qws, app_handle, "Año", anio, id=10)
            next_id = await aplicar_filtro(qws, app_handle, "Mes", mes, id=next_id)

            print("📊 Obteniendo tabla...")
            resp = await qws.send_recv(rpc_handle(app_handle, "GetObject", [OBJECT_ID], id=next_id))
            obj_handle = resp["result"]["qReturn"]["qHandle"]
            next_id += 1

            print("📐 Leyendo layout...")
            resp = await qws.send_recv(rpc_handle(obj_handle, "GetLayout", [], id=next_id))
            cube = resp["result"]["qLayout"]["qHyperCube"]
            total_rows  = cube["qSize"]["qcy"]
            total_cols  = cube["qSize"]["qcx"]
            headers_row = (
                [d["qFallbackTitle"] for d in cube["qDimensionInfo"]] +
                [m["qFallbackTitle"] for m in cube["qMeasureInfo"]]
            )
            print(f"   Filas: {total_rows:,} | Cols: {total_cols}")
        finally:
            qws.stop()

    if total_rows == 0:
        print("⚠️  Sin datos para el período solicitado.")
        return

    # --- Descarga en sesiones renovables ---
    total_chunks = (total_rows + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"\n⬇️  {total_rows:,} filas | {total_chunks} chunks | lotes de {MAX_PARALLEL}")

    all_rows  = [None] * total_rows
    processed = 0
    chunk_idx = 0

    while chunk_idx < total_chunks:
        async with websockets.connect(WS_URL, **ws_kwargs) as ws:
            qws = QlikWS(ws)
            qws.start()
            msg_id = 100
            try:
                resp = await qws.send_recv(rpc("OpenDoc", [APP_ID, "", "", "", False], id=msg_id))
                app_handle = resp["result"]["qReturn"]["qHandle"]
                msg_id += 1

                nid = await aplicar_filtro(qws, app_handle, "Año", anio, id=msg_id)
                nid = await aplicar_filtro(qws, app_handle, "Mes", mes, id=nid)
                msg_id = nid

                resp = await qws.send_recv(rpc_handle(app_handle, "GetObject", [OBJECT_ID], id=msg_id))
                obj_handle = resp["result"]["qReturn"]["qHandle"]
                msg_id += 1

                while chunk_idx < total_chunks:
                    batch_end = min(chunk_idx + MAX_PARALLEL, total_chunks)

                    tasks = []
                    for ci in range(chunk_idx, batch_end):
                        q_top    = ci * CHUNK_SIZE
                        q_height = min(CHUNK_SIZE, total_rows - q_top)
                        payload  = rpc_handle(
                            obj_handle, "GetHyperCubeData",
                            ["/qHyperCubeDef", [{
                                "qTop": q_top, "qLeft": 0,
                                "qHeight": q_height, "qWidth": total_cols,
                            }]],
                            id=msg_id,
                        )
                        tasks.append((q_top, qws.send_recv(payload)))
                        msg_id += 1

                    results = await asyncio.gather(*[t for _, t in tasks])

                    for (q_top, _), resp in zip(tasks, results):
                        matrix = resp["result"]["qDataPages"][0]["qMatrix"]
                        for i, row in enumerate(matrix):
                            all_rows[q_top + i] = [cell.get("qText", "") for cell in row]
                        processed += len(matrix)

                    chunk_idx = batch_end
                    pct = processed / total_rows * 100
                    print(f"\r   {processed:,}/{total_rows:,} ({pct:.1f}%)", end="", flush=True)
                    await asyncio.sleep(0.1)

            except ConnectionError:
                print(f"\n🔄 Reconectando desde chunk {chunk_idx}...")
            finally:
                qws.stop()

    # --- Escribir CSV ---
    fname = carpeta / f"gx_real_{anio}_{mes:02d}.csv"
    print(f"\n💾 Escribiendo CSV...")
    with open(fname, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers_row)
        writer.writerows(all_rows)

    print(f"✅ Guardado: {fname}")
    print(f"   Tamaño: {fname.stat().st_size / 1024 / 1024:.2f} MB")

# ==============================================================================
# ENTRY POINT
# ==============================================================================

def descargar_gx_real(anio: int, mes: int, carpeta: Path):
    asyncio.run(descargar(anio, mes, carpeta))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generación Real - Descarga desde Qlik")
    p.add_argument("--anio",    type=int,  required=True)
    p.add_argument("--mes",     type=int,  required=True)
    p.add_argument("--carpeta", type=Path, default=Path("data/gx_real"))
    args = p.parse_args()
    descargar_gx_real(args.anio, args.mes, args.carpeta)