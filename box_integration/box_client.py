import os
import json
from pathlib import Path
from boxsdk import OAuth2, Client
from dotenv import load_dotenv

# ✅ Carrega variáveis do .env APENAS localmente
if not os.getenv("RENDER"):
    load_dotenv()

# 🔍 DEBUG opcional
print(f"DEBUG: BOX_CLIENT_ID = {os.getenv('BOX_CLIENT_ID')}")
print(f"DEBUG: BOX_CLIENT_SECRET = {os.getenv('BOX_CLIENT_SECRET')}")

# ✅ Caminho do token (funciona no Render e localmente)
TOKENS_PATH = Path(__file__).resolve().parent.parent / 'box_tokens.json'


def load_tokens():
    print(f"DEBUG: Tentando carregar tokens do arquivo {TOKENS_PATH}")
    if not TOKENS_PATH.exists():
        print("DEBUG: Arquivo de tokens não existe.")
        return None, None
    with open(TOKENS_PATH, 'r') as f:
        data = json.load(f)
        print(f"DEBUG: Tokens carregados: {data}")
        return data.get('access_token'), data.get('refresh_token')


def save_tokens(access_token, refresh_token):
    print(f"DEBUG: Salvando tokens no arquivo {TOKENS_PATH}")
    with open(TOKENS_PATH, 'w') as f:
        json.dump({'access_token': access_token, 'refresh_token': refresh_token}, f)
    print("DEBUG: Tokens salvos com sucesso.")


def get_client():
    access_token, refresh_token = load_tokens()
    if not access_token or not refresh_token:
        raise Exception("Tokens não encontrados. Faça autenticação antes.")

    print("DEBUG: Criando OAuth2 com tokens carregados.")
    oauth = OAuth2(
        client_id=os.getenv('BOX_CLIENT_ID'),
        client_secret=os.getenv('BOX_CLIENT_SECRET'),
        access_token=access_token,
        refresh_token=refresh_token,
        store_tokens=save_tokens
    )
    client = Client(oauth)
    print("DEBUG: Cliente Box criado com sucesso.")
    return client


def upload_to_box(file_stream, filename, folder_name):
    try:
        print(f"DEBUG: Iniciando upload do arquivo '{filename}' para a pasta '{folder_name}' no Box.")
        client = get_client()
        root_folder = client.folder(folder_id='0')
        folders = root_folder.get_items()
        folder_id = None

        for item in folders:
            if item.type == 'folder' and item.name == folder_name:
                folder_id = item.id
                print(f"DEBUG: Pasta '{folder_name}' encontrada com ID: {folder_id}")
                break

        if folder_id is None:
            print(f"DEBUG: Pasta '{folder_name}' não encontrada, criando nova pasta.")
            new_folder = root_folder.create_subfolder(folder_name)
            folder_id = new_folder.id
            print(f"DEBUG: Nova pasta criada com ID: {folder_id}")

        folder = client.folder(folder_id=folder_id)

        # Remove arquivo se já existir
        for item in folder.get_items():
            if item.name == filename:
                print(f"DEBUG: Arquivo '{filename}' já existe. Deletando antes do upload.")
                item.delete()
                break

        file_stream.seek(0)
        folder.upload_stream(file_stream, filename)
        print(f"DEBUG: Upload do arquivo '{filename}' concluído com sucesso.")
        return f"✅ Arquivo '{filename}' enviado para Box na pasta '{folder_name}'."

    except Exception as e:
        print(f"ERROR: Erro ao enviar arquivo para Box: {repr(e)}")
        return f"❌ Erro ao enviar '{filename}' para Box: {repr(e)}"


# ✅ Função chamada ao receber o "code" via /callback (autenticação inicial)
def box_oauth2_callback(code):
    print("DEBUG: Autenticando via OAuth2 com código de autorização recebido.")

    # Determina qual redirect_uri usar
    redirect_uri = os.getenv("BOX_REDIRECT_URI", "http://localhost:5000/callback")

    oauth = OAuth2(
        client_id=os.getenv('BOX_CLIENT_ID'),
        client_secret=os.getenv('BOX_CLIENT_SECRET'),
        redirect_uri=redirect_uri,
    )
    access_token, refresh_token = oauth.authenticate(code)
    save_tokens(access_token, refresh_token)
    print("DEBUG: Autenticação concluída e tokens salvos.")
    return access_token, refresh_token


if __name__ == "__main__":
    # 🔧 Testes locais rápidos
    print("DEBUG: Testando carregamento de tokens e criação do cliente Box")
    try:
        client = get_client()
        user = client.user().get()
        print(f"DEBUG: Cliente Box funcionando! Usuário: {user.name} ({user.login})")
    except Exception as ex:
        print(f"ERROR: {ex}")
