import sys
import os


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from flask import Blueprint, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
from io import BytesIO, StringIO

from db.db_utils import connect_db, disconnect_db, insert_heroes_from_csv, insert_standings_from_csv, insert_pairings_from_csv, insert_calendar_entry
from box_integration.box_client import upload_to_box
from utils.helpers import allowed_file


upload_bp = Blueprint('upload', __name__, url_prefix='/upload')

@upload_bp.route('/', methods=['GET'])
def upload_page():
    return render_template('uploadcsv.html')

@upload_bp.route('/submit', methods=['POST'])
def upload_submit():
    conn = None
    try:
        # Validação dos campos
        required_fields = ['data', 'loja', 'formato']
        for field in required_fields:
            if not request.form.get(field):
                flash(f"❌ Campo obrigatório '{field}' não foi fornecido.", "error")
                return redirect(url_for('upload.upload_page'))

        # Validação dos arquivos
        files = {}
        for key in ['heroes', 'standings', 'pairings']:
            f = request.files.get(key)
            if not f or f.filename == '':
                flash(f"❌ Arquivo '{key}' não enviado.", "error")
                return redirect(url_for('upload.upload_page'))
            if not allowed_file(f.filename):
                flash(f"❌ Arquivo inválido: {f.filename}. Apenas CSV permitido.", "error")
                return redirect(url_for('upload.upload_page'))
            files[key] = f
       

        data = request.form['data'].strip()
        loja = request.form['loja'].strip()
        formato = request.form['formato'].strip()
        pasta_box = f"{loja}_{data}_{formato}"

        print("🔌 Conectando ao banco de dados...")
        conn = connect_db()
        cur = conn.cursor()
        

        # Processa CSVs
        
        result_heroes = insert_heroes_from_csv(StringIO(files['heroes'].read().decode('utf-8-sig')), data, loja, formato, cur)
        
        result_standings = insert_standings_from_csv(StringIO(files['standings'].read().decode('utf-8-sig')), data, loja, formato, cur)
        
        result_pairings = insert_pairings_from_csv(StringIO(files['pairings'].read().decode('utf-8-sig')), data, loja, formato, cur)
        
        calendar_result = insert_calendar_entry(data, loja, cur)
        

        # Faz upload para Box
        
        box_msgs = []
        for key in ['heroes', 'standings', 'pairings']:
            files[key].seek(0)
            msg = upload_to_box(BytesIO(files[key].read()), secure_filename(files[key].filename), pasta_box)
            box_msgs.append(msg)
            

        # Verifica falhas no Box
        if any(m.startswith("❌") for m in box_msgs):
            conn.rollback()
            
            flash("❌ Falha no upload para Box. Nenhum dado foi salvo.", "error")
            for msg in box_msgs:
                flash(msg, "error")
            return redirect(url_for('upload.upload_page'))

        # Se tudo certo, commit
        conn.commit()
        

        flash("✅ Dados salvos no banco e enviados para Box com sucesso.", "success")
        flash(result_heroes, "success")
        flash(result_standings, "success")
        flash(result_pairings, "success")
        flash(calendar_result, "info")

        return redirect(url_for('upload.upload_page'))

    except Exception as e:
        
        if conn:
            conn.rollback()
        flash(f"❌ Erro geral: {repr(e)}", "error")
        return redirect(url_for('upload.upload_page'))

    finally:
        if conn:
            disconnect_db(conn)
            