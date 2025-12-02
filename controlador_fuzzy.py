import matplotlib
matplotlib.use('Agg') # Evita travamentos de interface gráfica
import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import paho.mqtt.client as mqtt
import time
import json
import math

# --- CONFIGURAÇÕES MQTT ---
BROKER = "broker.mqtt-dashboard.com"
PORT = 1883
TOPIC_CTRL = "datacenter/fuzzy/control"
TOPIC_TEMP = "datacenter/fuzzy/temp"
TOPIC_ALERT = "datacenter/fuzzy/alert"
TOPIC_SET = "datacenter/fuzzy/set_params"

# --- ESTADO GLOBAL ---
modo_manual = False
simulacao_pausada = False
solicitacao_reset = False
params_manuais = {"setpoint": 22.0, "t_ext": 25.0, "q_est": 40.0}

# =============================================================================
# 1. FUZZY ROBUSTO
# =============================================================================
erro = ctrl.Antecedent(np.arange(-10, 11, 0.1), 'erro')
delta_erro = ctrl.Antecedent(np.arange(-2, 3, 0.1), 'delta_erro')
p_crac = ctrl.Consequent(np.arange(0, 101, 1), 'p_crac')

# Pertinência
erro['NG'] = fuzz.trapmf(erro.universe, [-10, -10, -3, -1.5])
erro['NP'] = fuzz.trimf(erro.universe, [-2, -1, 0])
erro['ZE'] = fuzz.trimf(erro.universe, [-0.5, 0, 0.5])
erro['PP'] = fuzz.trimf(erro.universe, [0, 1, 2])
erro['PG'] = fuzz.trapmf(erro.universe, [1.5, 3, 10, 10])

delta_erro['N'] = fuzz.trapmf(delta_erro.universe, [-2, -2, -0.5, 0])
delta_erro['Z'] = fuzz.trimf(delta_erro.universe, [-0.1, 0, 0.1])
delta_erro['P'] = fuzz.trapmf(delta_erro.universe, [0, 0.5, 2, 2])

# Saída
p_crac['P0'] = fuzz.trimf(p_crac.universe, [0, 0, 10])
p_crac['P1'] = fuzz.trimf(p_crac.universe, [5, 15, 25])
p_crac['P2'] = fuzz.trimf(p_crac.universe, [20, 30, 40])
p_crac['P3'] = fuzz.trimf(p_crac.universe, [35, 42, 50])
p_crac['P4'] = fuzz.trimf(p_crac.universe, [45, 50, 55])
p_crac['P5'] = fuzz.trimf(p_crac.universe, [50, 58, 65])
p_crac['P6'] = fuzz.trimf(p_crac.universe, [60, 70, 80])
p_crac['P7'] = fuzz.trimf(p_crac.universe, [75, 85, 95])
p_crac['P8'] = fuzz.trimf(p_crac.universe, [90, 100, 100])

# Regras
regras = []
regras.append(ctrl.Rule(erro['ZE'] & delta_erro['Z'], p_crac['P4'])) 
regras.append(ctrl.Rule(erro['ZE'] & delta_erro['P'], p_crac['P5']))
regras.append(ctrl.Rule(erro['ZE'] & delta_erro['N'], p_crac['P3']))
regras.append(ctrl.Rule(erro['PP'] & delta_erro['Z'], p_crac['P6']))
regras.append(ctrl.Rule(erro['PP'] & delta_erro['P'], p_crac['P7'])) 
regras.append(ctrl.Rule(erro['PP'] & delta_erro['N'], p_crac['P5'])) 
regras.append(ctrl.Rule(erro['NP'] & delta_erro['Z'], p_crac['P2']))
regras.append(ctrl.Rule(erro['NP'] & delta_erro['P'], p_crac['P3'])) 
regras.append(ctrl.Rule(erro['NP'] & delta_erro['N'], p_crac['P1'])) 
regras.append(ctrl.Rule(erro['PG'], p_crac['P8'])) 
regras.append(ctrl.Rule(erro['NG'], p_crac['P0'])) 

sistema_controle = ctrl.ControlSystem(regras)
simulador_fuzzy = ctrl.ControlSystemSimulation(sistema_controle)

# =============================================================================
# 2. MODELO FÍSICO
# =============================================================================
def modelo_fisico_pdf(t_atual, p_crac, q_est, t_ext):
    t_next = (0.9 * t_atual) - (0.08 * p_crac) + (0.05 * q_est) + (0.02 * t_ext) + 3.5
    return t_next

def on_connect(client, userdata, flags, rc):
    print(f"MQTT Conectado (rc: {rc})")
    client.subscribe(TOPIC_SET)

def on_message(client, userdata, msg):
    global modo_manual, params_manuais, simulacao_pausada, solicitacao_reset
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("cmd") == "PAUSE":
            simulacao_pausada = True
            print("--- PAUSE ---")
        elif payload.get("cmd") == "PLAY":
            simulacao_pausada = False
            print("--- PLAY ---")
        elif payload.get("cmd") == "RESTART":
            solicitacao_reset = True
            print("--- RESET ---")
        elif payload.get("mode") == "MANUAL":
            modo_manual = True
            params_manuais.update(payload)
        elif payload.get("mode") == "AUTO":
            modo_manual = False
            print("Modo AUTO (Variáveis Constantes).")
    except Exception as e:
        print(f"Erro payload: {e}")

def main():
    # DECLARAÇÃO GLOBAL NO INÍCIO PARA EVITAR SYNTAX ERROR
    global solicitacao_reset, simulacao_pausada 
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    t_atual = 22.0
    p_crac_atual = 47.5
    erro_anterior = 0.0
    entradas_oxigenio = True
    modo_incendio = False
    minuto = 0
    simulacao_pausada = False

    print("\n--- INICIANDO SIMULAÇÃO 24H (CONSTANTE) ---")

    while True:
        # Reset
        if solicitacao_reset:
            minuto = 0
            t_atual = 22.0
            p_crac_atual = 47.5
            erro_anterior = 0.0
            entradas_oxigenio = True
            modo_incendio = False
            simulacao_pausada = False
            solicitacao_reset = False
            client.publish(TOPIC_CTRL, json.dumps({"status": "RESET", "tempo": 0}))
            time.sleep(0.5)

        # Fim 24h
        if minuto >= 1440 and not simulacao_pausada:
            simulacao_pausada = True
            print("--- FIM DO CICLO 24H ---")
            client.publish(TOPIC_ALERT, json.dumps({"tipo": "INFO", "msg": "Ciclo Concluído", "valor": 24}))

        # Pausa
        while simulacao_pausada and not solicitacao_reset:
            time.sleep(0.5)
            status_msg = "CONCLUIDO" if minuto >= 1440 else "PAUSADO"
            client.publish(TOPIC_CTRL, json.dumps({"modo": status_msg}))
            continue

        # Definição de Variáveis
        if modo_manual:
            setpoint = float(params_manuais["setpoint"])
            t_ext_val = float(params_manuais["t_ext"])
            q_est_val = float(params_manuais["q_est"])
        else:
            setpoint = 22.0
            # --- CONSTANTES CONFORME SOLICITADO ---
            t_ext_val = 25.0
            q_est_val = 40.0
            # --------------------------------------

        # Perturbação (Fogo às 14:00)
        if not modo_manual and 840 <= minuto < 845 and not modo_incendio:
            t_atual += 8.0

        # Fuzzy
        erro_val = t_atual - setpoint
        var_erro = erro_val - erro_anterior
        
        simulador_fuzzy.input['erro'] = np.clip(erro_val, -10, 10)
        simulador_fuzzy.input['delta_erro'] = np.clip(var_erro, -2, 2)

        # Incêndio
        if (t_atual > 30.0) and (var_erro > 1.5):
            modo_incendio = True
            entradas_oxigenio = False
        
        if modo_incendio and t_atual < 25.0:
            modo_incendio = False
            entradas_oxigenio = True

        if modo_incendio:
            q_est_val = 100
            if not entradas_oxigenio: t_atual -= 0.4
            else: t_atual += 1.0

        try:
            simulador_fuzzy.compute()
            p_crac_nova = simulador_fuzzy.output['p_crac']
        except:
            p_crac_nova = p_crac_atual

        # Física
        if not modo_incendio:
            t_next = modelo_fisico_pdf(t_atual, p_crac_nova, q_est_val, t_ext_val)
        else:
            t_next = t_atual

        # Alertas
        alert_msg = None
        tipo_alerta = "NORMAL"
        if not entradas_oxigenio:
            tipo_alerta = "FOGO"
            alert_msg = "INCÊNDIO: O2 CORTADO"
        elif t_next > 26.0:
            tipo_alerta = "ALTA"
            alert_msg = "ALERTA: T > 26°C"
        elif t_next < 18.0:
            tipo_alerta = "BAIXA"
            alert_msg = "ALERTA: T < 18°C"
        
        if alert_msg:
             client.publish(TOPIC_ALERT, json.dumps({"tipo": tipo_alerta, "msg": alert_msg, "valor": round(t_next, 1)}))
        
        # Publicação
        dados = {
            "tempo": minuto, "setpoint": setpoint, "p_crac": round(p_crac_nova, 2),
            "t_ext": round(t_ext_val, 2), "q_est": round(q_est_val, 2),
            "oxigenio": "ABERTO" if entradas_oxigenio else "FECHADO",
            "modo": "MANUAL" if modo_manual else "AUTO"
        }
        client.publish(TOPIC_CTRL, json.dumps(dados))
        client.publish(TOPIC_TEMP, json.dumps({"tempo": minuto, "temperatura": round(t_next, 2)}))

        erro_anterior = erro_val
        t_atual = t_next
        p_crac_atual = p_crac_nova
        minuto += 1
        time.sleep(0.1)

if __name__ == "__main__":
    main()