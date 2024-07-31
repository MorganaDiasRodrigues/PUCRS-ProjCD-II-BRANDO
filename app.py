import gradio as gr
import mysql.connector
import json
import datetime
from openai import OpenAI
import re

# Configuração da API do OpenAI
api_key = ""
openai = OpenAI(
    api_key=api_key,
    base_url="",
)

# Configuração do banco de dados
cnx = mysql.connector.connect(
    host="",
    user="",
    password="",
    database=""
)
cursor = cnx.cursor()

# Função para processar a entrada SQL e chamar a LLM
def process_query(input_query):
    cursor.execute(input_query)
    output = cursor.fetchall()

    table_name_match = re.search(r'FROM\s+(\w+)', cursor.statement, re.IGNORECASE)
    if table_name_match:
        table_name = table_name_match.group(1)
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        columns = cursor.fetchall()
    else:
        return "Table não encontrada na query."

    path = r"database_information.json"
    with open(path, encoding='utf-8') as f:
        brando_dict = json.load(f)

    key_words = {}
    if len(output) > 1:
        print(f"Paciente com {len(output)} registros.")

    for registro in output:
        key_words[registro[0]] = []  # posicao 0 esta o numero do registro
        for column, value in zip(columns, registro):
            if value is not None:
                try:
                    if brando_dict[table_name][column[0]]['Labels & options'] == {}:
                        pass
                    else:
                        if type(value) == str:
                            for key, label in brando_dict[table_name][column[0]]['Labels & options'].items():
                                if label.upper().startswith(value.upper()) or label.upper().startswith(key.upper()):
                                    key_words[registro[0]].append({brando_dict[table_name][column[0]]['column_explanation']: label})
                    if isinstance(value, datetime.date):
                        key_words[registro[0]].append({brando_dict[table_name][column[0]]['column_explanation']: value.strftime('%Y-%m-%d')})

                except KeyError:
                    pass

    responses = []
    for registro, detalhes_consulta in key_words.items():
        chat_completion = openai.chat.completions.create(
            model="meta-llama/Meta-Llama-3-70B-Instruct",
            messages=[{"role": "user", 
                       "content": f"[pt/br] Baseando-se nestes detalhes de registro histórico de um paciente, faça um texto breve destes registros. Registro da consulta: {registro}. Detalhes: {detalhes_consulta}"}]
        )

        responses.append(chat_completion.choices[0].message.content)
    
    return "\n\n".join(responses)

# Configuração da interface Gradio
iface = gr.Interface(
    fn=process_query,
    inputs=gr.Textbox(lines=5, label="Consulta SQL"),
    outputs=gr.Textbox(label="Resumo Gerado pela LLM"),
    title="Consulta SQL e Resumo LLM",
    description="Digite uma consulta SQL para obter registros do banco de dados e gerar um resumo usando um modelo de linguagem.",
)

# Inicia a interface
iface.launch()
