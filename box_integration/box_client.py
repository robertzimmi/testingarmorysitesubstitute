import os
import json
from io import BytesIO
from boxsdk import OAuth2, Client

# Salva os tokens em um arquivo local
def save_tokens(access_token, refresh_token):
    print("🔄 Salvando novos tokens...")
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token
    }
    with open("box_tokens.json", "w") as f:
        json.dump(token_data, f)
    print("✅ Tokens salvos em 'box_tokens.json'.")

# Carrega os tokens do arquivo ou das variáveis de ambiente
def load_tokens():
    try:
        with open("box_tokens.json", "r") as f:
            tokens = json.load(f)
            return tokens["access_token"], tokens["refresh_token"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return os.environ.get("BOX_ACCESS_TOKEN"), os.environ.get("BOX_REFRESH_TOKEN")

def upload_to_box(file_stream: BytesIO, file_name: str, folder_name: str) -> str:
    print(f"🔄 Iniciando upload do arquivo '{file_name}' para a pasta '{folder_name}' no Box...")

    # Carrega tokens
    access_token, refresh_token = load_tokens()
    if not access_token or not refresh_token:
        print("❌ Tokens de acesso ou refresh não encontrados.")
        return "❌ BOX_ACCESS_TOKEN ou BOX_REFRESH_TOKEN não configurados ou salvos."

    print("🔐 Tokens carregados com sucesso.")

    oauth = OAuth2(
        client_id=os.getenv("BOX_CLIENT_ID"),
        client_secret=os.getenv("BOX_CLIENT_SECRET"),
        access_token=access_token,
        refresh_token=refresh_token,
        store_tokens=save_tokens  # Agora salvando de verdade!
    )

    try:
        client = Client(oauth)
        print("✅ Cliente Box inicializado.")

        # Procurar ou criar pasta
        print("📁 Verificando existência da pasta...")
        root_folder = client.folder('0')
        folder_id = None

        for item in root_folder.get_items():
            print(f"📦 Item encontrado: {item.type} - {item.name}")
            if item.type == 'folder' and item.name == folder_name:
                folder_id = item.id
                print(f"✅ Pasta '{folder_name}' encontrada. ID: {folder_id}")
                break

        if folder_id is None:
            print(f"📁 Pasta '{folder_name}' não encontrada. Criando...")
            folder_id = root_folder.create_subfolder(folder_name).id
            print(f"✅ Pasta criada. ID: {folder_id}")

        folder = client.folder(folder_id)

        # Verificar se o arquivo já existe
        existing_file = None
        for item in folder.get_items():
            if item.type == 'file' and item.name == file_name:
                existing_file = item
                print(f"♻️ Arquivo existente encontrado: {file_name}")
                break

        file_stream.seek(0)

        if existing_file:
            print(f"⬆️ Atualizando conteúdo de '{file_name}'...")
            updated_file = existing_file.update_contents(file_stream)
            return f"✅ Arquivo '{updated_file.name}' atualizado com sucesso na pasta '{folder_name}'!"
        else:
            print(f"⬆️ Enviando novo arquivo '{file_name}'...")
            uploaded_file = folder.upload_stream(file_stream, file_name)
            return f"✅ Arquivo '{uploaded_file.name}' enviado para a pasta '{folder_name}' no Box com sucesso!"

    except Exception as e:
        print(f"❌ Exceção ao enviar arquivo para o Box: {repr(e)}")
        return f"❌ Erro ao enviar arquivo para o Box: {repr(e)}"
