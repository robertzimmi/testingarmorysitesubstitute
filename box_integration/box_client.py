import os
import json
from boxsdk import OAuth2, Client

TOKENS_PATH = 'box_tokens.json'  # Corrija aqui conforme o nome correto do arquivo

def load_tokens():
    if not os.path.exists(TOKENS_PATH):
        return None, None
    with open(TOKENS_PATH, 'r') as f:
        data = json.load(f)
        return data.get('access_token'), data.get('refresh_token')

def save_tokens(access_token, refresh_token):
    with open(TOKENS_PATH, 'w') as f:
        json.dump({'access_token': access_token, 'refresh_token': refresh_token}, f)
    print(f"[TOKENS SALVOS] Novo access_token: {access_token[:8]}..., refresh_token: {refresh_token[:8]}...")

def get_client():
    access_token, refresh_token = load_tokens()
    if not access_token or not refresh_token:
        raise Exception("Tokens não encontrados. Faça autenticação.")

    oauth = OAuth2(
        client_id=os.getenv('BOX_CLIENT_ID'),
        client_secret=os.getenv('BOX_CLIENT_SECRET'),
        access_token=access_token,
        refresh_token=refresh_token,
        store_tokens=save_tokens
    )

    client = Client(oauth)

    # 🧪 Forçar uma chamada para validar/renovar o token
    try:
        print("[DEBUG] Testando validade do token com chamada ao perfil do usuário Box...")
        _ = client.user().get()  # Isso força a renovação se necessário
    except Exception as e:
        print(f"[Box] Erro ao validar token: {e}")
        raise Exception("Token de acesso inválido ou expirado. Reautentique o app.")

    return client

def upload_to_box(file_stream, filename, folder_name):
    try:
        client = get_client()
        root_folder = client.folder(folder_id='0')
        folders = root_folder.get_items()
        folder_id = None
        for item in folders:
            if item.type == 'folder' and item.name == folder_name:
                folder_id = item.id
                break
        if folder_id is None:
            new_folder = root_folder.create_subfolder(folder_name)
            folder_id = new_folder.id

        folder = client.folder(folder_id=folder_id)
        items = folder.get_items()
        for item in items:
            if item.name == filename:
                item.delete()
                break

        file_stream.seek(0)  # Garantir que o ponteiro está no início antes de enviar
        folder.upload_stream(file_stream, filename)
        return f"✅ Arquivo '{filename}' enviado para Box na pasta '{folder_name}'."
    except Exception as e:
        return f"❌ Erro ao enviar '{filename}' para Box: {repr(e)}"
