import os
import json
from io import BytesIO
from boxsdk import OAuth2, Client

TOKENS_PATH = 'box_tokens.json'  # arquivo local para guardar tokens


def load_tokens():
    if not os.path.exists(TOKENS_PATH):
        return None, None
    with open(TOKENS_PATH, 'r') as f:
        data = json.load(f)
        return data.get('access_token'), data.get('refresh_token')


def save_tokens(access_token, refresh_token):
    with open(TOKENS_PATH, 'w') as f:
        json.dump({'access_token': access_token, 'refresh_token': refresh_token}, f)


def upload_to_box(file_stream: BytesIO, file_name: str, folder_name: str) -> str:
    access_token, refresh_token = load_tokens()

    oauth = OAuth2(
        client_id=os.getenv("BOX_CLIENT_ID"),
        client_secret=os.getenv("BOX_CLIENT_SECRET"),
        access_token=access_token,
        refresh_token=refresh_token,
        store_tokens=save_tokens
    )

    client = Client(oauth)

    try:
        root_folder = client.folder('0')

        folder_id = None
        for item in root_folder.get_items():
            if item.type == 'folder' and item.name == folder_name:
                folder_id = item.id
                break

        if folder_id is None:
            folder_id = root_folder.create_subfolder(folder_name).id

        folder = client.folder(folder_id)

        existing_file = None
        for item in folder.get_items():
            if item.type == 'file' and item.name == file_name:
                existing_file = item
                break

        file_stream.seek(0)

        if existing_file:
            updated_file = existing_file.update_contents(file_stream)
            return f"✅ Arquivo '{updated_file.name}' atualizado com sucesso na pasta '{folder_name}'!"
        else:
            uploaded_file = folder.upload_stream(file_stream, file_name)
            return f"✅ Arquivo '{uploaded_file.name}' enviado para a pasta '{folder_name}' no Box com sucesso!"

    except Exception as e:
        return f"❌ Erro ao enviar arquivo para o Box: {repr(e)}"
