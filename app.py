from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from models import db, Usuario, Produto, Fornecedor, Venda, ItemVenda, Compra, ItemCompra, Devolucao, ItemDevolucao, Saldo, DevolucaoCompra, ItemDevolucaoCompra
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func, extract
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors

from produtos_blueprint import produtos_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(os.getcwd(), "farmacia.db")}'
print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa db e login
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

# ===================== Roteamento de Blueprints =====================
app.register_blueprint(produtos_bp, url_prefix='/produtos')

# ===================== LOGIN =====================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_login = request.form.get('usuario')
        senha = request.form.get('senha')
        user = Usuario.query.filter_by(usuario = usuario_login).first()
        if user and check_password_hash(user.senha, senha):
            login_user(user)
            flash(f'Bem-vindo {user.nome}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha incorretos', 'danger')
    return render_template('login.html')

# ===================== LOGOUT =====================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

# ===================== DASHBOARD GERAL =====================
@app.route('/dashboard')
@login_required
def dashboard():
    produtos_total = Produto.query.count()
    usuarios_total = Usuario.query.count()
    fornecedores_total = Fornecedor.query.count()
    hoje = datetime.now().date()
    daqui_30_dias = hoje + timedelta(days=30)
    produtos_vencendo = Produto.query.filter(Produto.validade >= hoje, Produto.validade <= daqui_30_dias).count()
    produtos_vendidos = db.session.query(func.sum(ItemVenda.quantidade)).scalar() or 0
    produtos_devolvidos = db.session.query(func.sum(ItemDevolucao.quantidade)).scalar() or 0
    vendas_hoje = Venda.query.filter(Venda.data >= hoje, Venda.data < hoje + timedelta(days=1)).all()
    compras_hoje = Compra.query.filter(Compra.data >= hoje, Compra.data < hoje + timedelta(days=1)).all()
    total_vendas_hoje = len(vendas_hoje)

    # Alertas de estoque
    produtos_criticos = Produto.query.filter(Produto.quantidade <= 10).all()
    produtos_poucos = Produto.query.filter(Produto.quantidade > 10, Produto.quantidade <= 20).all()
    produtos_medios = Produto.query.filter(Produto.quantidade > 20, Produto.quantidade <= 50).all()

    # Saldo
    saldo = Saldo.query.first()
    saldo_valor = saldo.valor if saldo else 0.0

    return render_template('dashboard.html', produtos_total=produtos_total,
                           usuarios_total=usuarios_total,
                           fornecedores_total=fornecedores_total,
                           produtos_vencendo=produtos_vencendo,
                           produtos_vendidos=produtos_vendidos,
                           produtos_devolvidos=produtos_devolvidos,
                           vendas_hoje=vendas_hoje, compras_hoje=compras_hoje,
                           total_vendas_hoje=total_vendas_hoje,
                           produtos_criticos=produtos_criticos,
                           produtos_poucos=produtos_poucos,
                           produtos_medios=produtos_medios,
                           saldo=saldo_valor,
                           user_tipo=current_user.tipo)

# ===================== CRUD USUÁRIOS =====================
@app.route('/usuarios')
@login_required
def listar_usuarios():
    if current_user.tipo != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    usuarios = Usuario.query.order_by(Usuario.id).all()
    return render_template('usuarios/listar_usuarios.html', usuarios=usuarios)

@app.route('/usuarios/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_usuario():
    if current_user.tipo != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        novo = Usuario(
            nome=request.form['nome'],
            usuario=request.form['usuario'],
            senha=generate_password_hash(request.form['senha']),
            tipo=request.form['tipo']
        )
        db.session.add(novo)
        db.session.commit()
        flash('Usuário adicionado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
    return render_template('usuarios/adicionar_usuario.html')

@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if current_user.tipo != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    usuario = Usuario.query.get_or_404(id)
    if request.method == 'POST':
        usuario.nome = request.form['nome']
        usuario.usuario = request.form['usuario']
        if request.form['senha']:
            usuario.senha = generate_password_hash(request.form['senha'])
        usuario.tipo = request.form['tipo']
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
    return render_template('usuarios/editar_usuario.html', usuario=usuario)

@app.route('/usuarios/excluir/<int:id>')
@login_required
def excluir_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('listar_usuarios'))

# ===================== CRUD FORNECEDORES =====================
@app.route('/fornecedores')
@login_required
def listar_fornecedores():
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    fornecedores = Fornecedor.query.order_by(Fornecedor.id).all()
    return render_template('fornecedores/listar_fornecedores.html', fornecedores=fornecedores)

@app.route('/fornecedores/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_fornecedor():
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        novo = Fornecedor(
            nome=request.form['nome'],
            contato=request.form.get('contato'),
            telefone=request.form.get('telefone'),
            email=request.form.get('email'),
            endereco=request.form.get('endereco')
        )
        db.session.add(novo)
        db.session.commit()
        flash('Fornecedor adicionado com sucesso!', 'success')
        return redirect(url_for('listar_fornecedores'))
    return render_template('fornecedores/adicionar_fornecedor.html')

@app.route('/fornecedores/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_fornecedor(id):
    if current_user.tipo != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    fornecedor = Fornecedor.query.get_or_404(id)
    if request.method == 'POST':
        fornecedor.nome = request.form['nome']
        fornecedor.contato = request.form.get('contato')
        fornecedor.telefone = request.form.get('telefone')
        fornecedor.email = request.form.get('email')
        fornecedor.endereco = request.form.get('endereco')
        db.session.commit()
        flash('Fornecedor atualizado com sucesso!', 'success')
        return redirect(url_for('listar_fornecedores'))
    return render_template('fornecedores/editar_fornecedor.html', fornecedor=fornecedor)

@app.route('/fornecedores/excluir/<int:id>')
@login_required
def excluir_fornecedor(id):
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    fornecedor = Fornecedor.query.get_or_404(id)
    db.session.delete(fornecedor)
    db.session.commit()
    flash('Fornecedor excluído com sucesso!', 'success')
    return redirect(url_for('listar_fornecedores'))

# ===================== CRUD VENDAS =====================
from models import Venda, ItemVenda

@app.route('/vendas')
@login_required
def listar_vendas():
    if current_user.tipo not in ['Admin', 'Atendente']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    vendas = Venda.query.order_by(Venda.data.desc()).all()
    return render_template('vendas/listar_vendas.html', vendas=vendas)

@app.route('/vendas/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_venda():
    if current_user.tipo not in ['Admin', 'Atendente']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        import json
        itens = json.loads(request.form['itens'])
        total = float(request.form['total'])
        forma_pagamento = request.form['forma_pagamento']
        data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()

        nova_venda = Venda(total=total, usuario_id=current_user.id, forma_pagamento=forma_pagamento, data=data)
        db.session.add(nova_venda)
        db.session.flush()  # Para obter o ID da venda

        for item in itens:
            produto = Produto.query.get(item['id'])
            if produto:
                item_venda = ItemVenda(venda_id=nova_venda.id, produto_id=item['id'], quantidade=item['quantidade'], preco_unitario=item['preco'])
                db.session.add(item_venda)
                # Atualizar estoque
                produto.quantidade -= item['quantidade']
                if produto.quantidade <= 0:
                    db.session.delete(produto)

        # Adicionar ao saldo
        saldo = Saldo.query.first()
        if not saldo:
            saldo = Saldo(valor=0.0)
            db.session.add(saldo)
        saldo.valor += total

        db.session.commit()
        flash('Venda adicionada com sucesso!', 'success')
        # return redirect(url_for('listar_vendas'))
        return render_template('fatura.html', venda=nova_venda)
    produtos = Produto.query.filter(Produto.quantidade > 0).all()
    return render_template('vendas/adicionar_venda.html', produtos=produtos, datetime=datetime)

@app.route('/vendas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_venda(id):
    if current_user.tipo not in ['Admin', 'Atendente']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('listar_vendas'))
    venda = Venda.query.get_or_404(id)
    if request.method == 'POST':
        import json
        itens = json.loads(request.form['itens'])
        total = float(request.form['total'])
        forma_pagamento = request.form['forma_pagamento']
        data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()

        # Primeiro, devolver os produtos ao estoque
        for item in venda.itens:
            item.produto.quantidade += item.quantidade

        # Deletar itens antigos
        ItemVenda.query.filter_by(venda_id=id).delete()

        # Atualizar venda
        venda.total = total
        venda.forma_pagamento = forma_pagamento
        venda.data = data

        # Adicionar novos itens
        for item in itens:
            produto = Produto.query.get(item['id'])
            if produto:
                item_venda = ItemVenda(venda_id=venda.id, produto_id=item['id'], quantidade=item['quantidade'], preco_unitario=item['preco'])
                db.session.add(item_venda)
                # Atualizar estoque
                produto.quantidade -= item['quantidade']
                if produto.quantidade <= 0:
                    db.session.delete(produto)

        db.session.commit()
        flash('Venda atualizada com sucesso!', 'success')
        return redirect(url_for('listar_vendas'))

    produtos = Produto.query.all()  # Todos os produtos, mesmo sem estoque, para edição
    return render_template('vendas/editar_venda.html', venda=venda, produtos=produtos, datetime=datetime)

@app.route('/vendas/excluir/<int:id>')
@login_required
def excluir_venda(id):
    if current_user.tipo != 'Admin':
        flash('Acesso negado. Apenas Admin pode excluir vendas.', 'danger')
        return redirect(url_for('listar_vendas'))
    venda = Venda.query.get_or_404(id)
    db.session.delete(venda)
    db.session.commit()
    flash('Venda excluída com sucesso!', 'success')
    return redirect(url_for('listar_vendas'))

@app.route('/vendas/fatura/<int:venda_id>/pdf')
@login_required
def gerar_pdf_fatura(venda_id):
    venda = Venda.query.get_or_404(venda_id)
    if current_user.tipo not in ['Admin', 'Atendente'] or venda.usuario_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('listar_vendas'))

    # Tamanho A6 aproximado: 297 x 420 pontos
    page_width, page_height = 297, 420
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(page_width, page_height), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    elements = []

    # Estilo personalizado
    title_style = styles['Heading2']
    title_style.alignment = 1  # Centro
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    bold_style = styles['Normal']
    bold_style.fontName = 'Helvetica-Bold'
    bold_style.fontSize = 10

    # Cabeçalho com Logo (assumindo logo.png no static)
    try:
        logo_path = os.path.join(app.root_path, 'static', 'logo.png')
        if os.path.exists(logo_path):
            elements.append(Paragraph('<img src="{}" width="100" height="50"/>'.format(logo_path), normal_style))
    except:
        pass

    # Nome da Farmácia
    elements.append(Paragraph("Farmácia XYZ", title_style))
    elements.append(Paragraph("Endereço: Rua Exemplo, 123 - Cidade, Estado", normal_style))
    elements.append(Paragraph("Telefone: (11) 1234-5678 | Email: contato@farmaciaxyz.com", normal_style))
    elements.append(Paragraph(" ", normal_style))  # Espaço

    # Título da Fatura
    elements.append(Paragraph("FATURA DE VENDA", title_style))
    elements.append(Paragraph(" ", normal_style))

    # Informações da Venda
    info_data = [
        [Paragraph("<b>Número da Venda:</b> {}".format(venda.id), normal_style), Paragraph("<b>Data/Hora:</b> {}".format(venda.data.strftime('%d/%m/%Y %H:%M')), normal_style)],
        [Paragraph("<b>Atendente:</b> {}".format(venda.usuario.nome), normal_style), Paragraph("<b>Forma de Pagamento:</b> {}".format(venda.forma_pagamento), normal_style)],
    ]
    info_table = Table(info_data, colWidths=[page_width/2 - 25, page_width/2 - 25])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Paragraph(" ", normal_style))

    # Tabela de Itens
    data = [['Produto', 'Qtd', 'Preço Unit.', 'Subtotal']]
    for item in venda.itens:
        data.append([
            item.produto.nome,
            str(item.quantidade),
            "R$ {:.2f}".format(item.preco_unitario),
            "R$ {:.2f}".format(item.quantidade * item.preco_unitario)
        ])
    data.append(['', '', 'TOTAL:', "R$ {:.2f}".format(venda.total)])

    table = Table(data, colWidths=[page_width*0.4, page_width*0.15, page_width*0.2, page_width*0.25])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (1, 1), (3, -2), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    elements.append(table)

    # Rodapé
    elements.append(Paragraph(" ", normal_style))
    elements.append(Paragraph("Obrigado pela preferência!", normal_style))
    elements.append(Paragraph("Esta é uma fatura digital. Conserve para seus registros.", normal_style))

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'fatura_venda_{venda.id}.pdf', mimetype='application/pdf')

# ===================== COMPRAS =====================
@app.route('/compras')
@login_required
def listar_compras():
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    compras = Compra.query.order_by(Compra.data.desc()).all()
    return render_template('compras/listar_compras.html', compras=compras)

@app.route('/compras/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_compra():
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        import json
        itens = json.loads(request.form['itens'])
        total = float(request.form['total'])
        fornecedor_id = int(request.form['fornecedor_id'])
        data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()

        # Verificar saldo
        saldo = Saldo.query.first()
        if not saldo:
            saldo = Saldo(valor=0.0)
            db.session.add(saldo)
        if total > saldo.valor:
            flash('Saldo insuficiente para realizar a compra.', 'danger')
            return redirect(url_for('adicionar_compra'))

        nova_compra = Compra(total=total, fornecedor_id=fornecedor_id, usuario_id=current_user.id, data=data)
        db.session.add(nova_compra)
        db.session.flush()

        for item in itens:
            produto = Produto.query.get(item['id'])
            if produto:
                item_compra = ItemCompra(compra_id=nova_compra.id, produto_id=item['id'], quantidade=item['quantidade'], preco_unitario=item['preco'])
                db.session.add(item_compra)
                # Atualizar estoque
                produto.quantidade += item['quantidade']

        # Subtrair do saldo
        saldo.valor -= total
        db.session.commit()
        flash('Compra adicionada com sucesso!', 'success')
        return redirect(url_for('listar_compras'))
    produtos = Produto.query.all()
    fornecedores = Fornecedor.query.all()
    return render_template('compras/adicionar_compra.html', produtos=produtos, fornecedores=fornecedores, datetime=datetime)

@app.route('/compras/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_compra(id):
    # Gestores e Admins podem editar compras
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))

    compra = Compra.query.get_or_404(id)

    if request.method == 'POST':
        import json
        itens = json.loads(request.form['itens'])
        fornecedor_id = int(request.form['fornecedor_id'])
        data = datetime.strptime(request.form['data'], '%Y-%m-%d')
        total = float(request.form['total'])

        # Verificar saldo para diferença de valores
        saldo = Saldo.query.first()
        if not saldo:
            saldo = Saldo(valor=0.0)
            db.session.add(saldo)

        diferenca = total - compra.total
        if diferenca > 0 and diferenca > saldo.valor:
            flash('Saldo insuficiente para atualizar a compra.', 'danger')
            return redirect(url_for('editar_compra', id=id))

        # Reverter estoque dos itens antigos
        for item in compra.itens:
            item.produto.quantidade -= item.quantidade

        # Remover itens antigos
        ItemCompra.query.filter_by(compra_id=id).delete()

        # Adicionar novos itens e atualizar estoque
        for item in itens:
            produto = Produto.query.get(item['id'])
            if produto:
                item_compra = ItemCompra(compra_id=compra.id, produto_id=item['id'], quantidade=item['quantidade'], preco_unitario=item['preco'])
                db.session.add(item_compra)
                produto.quantidade += item['quantidade']

        # Atualizar dados da compra
        compra.total = total
        compra.fornecedor_id = fornecedor_id
        compra.data = data

        # Ajustar saldo com a diferença
        saldo.valor -= diferenca

        db.session.commit()
        flash('Compra atualizada com sucesso!', 'success')
        return redirect(url_for('listar_compras'))

    produtos = Produto.query.all()
    fornecedores = Fornecedor.query.all()
    return render_template('compras/editar_compra.html', compra=compra, produtos=produtos, fornecedores=fornecedores, datetime=datetime)

# ===================== DEVOLUÇÕES DE COMPRA =====================
@app.route('/devolucoes_compra')
@login_required
def listar_devolucoes_compra():
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    devolucoes = DevolucaoCompra.query.order_by(DevolucaoCompra.data.desc()).all()
    return render_template('devolucoes_compra/listar_devolucoes_compra.html', devolucoes=devolucoes)

@app.route('/devolucoes_compra/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_devolucao_compra():
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        import json
        itens = json.loads(request.form['itens'])
        motivo = request.form['motivo']
        fornecedor_id = int(request.form['fornecedor_id'])

        nova_devolucao = DevolucaoCompra(motivo=motivo, fornecedor_id=fornecedor_id, usuario_id=current_user.id)
        db.session.add(nova_devolucao)
        db.session.flush()

        total_devolvido = 0
        for item in itens:
            produto = Produto.query.get(item['id'])
            if produto:
                item_devolucao = ItemDevolucaoCompra(devolucao_compra_id=nova_devolucao.id, produto_id=item['id'], quantidade=item['quantidade'])
                db.session.add(item_devolucao)
                # Aumentar estoque
                produto.quantidade += item['quantidade']
                # Calcular valor devolvido (baseado no preço de compra)
                total_devolvido += item['quantidade'] * produto.preco_compra

        # Adicionar ao saldo
        saldo = Saldo.query.first()
        if not saldo:
            saldo = Saldo(valor=0.0)
            db.session.add(saldo)
        saldo.valor += total_devolvido

        db.session.commit()
        flash('Devolução de compra realizada com sucesso!', 'success')
        return redirect(url_for('listar_devolucoes_compra'))

    produtos = Produto.query.all()
    fornecedores = Fornecedor.query.all()
    return render_template('devolucoes_compra/adicionar_devolucao_compra.html', produtos=produtos, fornecedores=fornecedores)

@app.route('/devolucoes_compra/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_devolucao_compra(id):
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    devolucao = DevolucaoCompra.query.get_or_404(id)
    if request.method == 'POST':
        import json
        itens = json.loads(request.form['itens'])
        motivo = request.form['motivo']
        fornecedor_id = int(request.form['fornecedor_id'])

        # Primeiro, reverter os itens antigos
        for item in devolucao.itens:
            item.produto.quantidade -= item.quantidade

        # Deletar itens antigos
        ItemDevolucaoCompra.query.filter_by(devolucao_compra_id=id).delete()

        # Atualizar devolução
        devolucao.motivo = motivo
        devolucao.fornecedor_id = fornecedor_id

        # Adicionar novos itens
        total_devolvido = 0
        for item in itens:
            produto = Produto.query.get(item['id'])
            if produto:
                item_devolucao = ItemDevolucaoCompra(devolucao_compra_id=devolucao.id, produto_id=item['id'], quantidade=item['quantidade'])
                db.session.add(item_devolucao)
                produto.quantidade += item['quantidade']
                total_devolvido += item['quantidade'] * produto.preco_compra

        # Ajustar saldo (subtrair antigo e adicionar novo)
        saldo = Saldo.query.first()
        if saldo:
            # Calcular antigo
            antigo_total = sum(item.quantidade * item.produto.preco_compra for item in devolucao.itens)
            saldo.valor -= antigo_total
            saldo.valor += total_devolvido

        db.session.commit()
        flash('Devolução de compra atualizada com sucesso!', 'success')
        return redirect(url_for('listar_devolucoes_compra'))

    produtos = Produto.query.all()
    fornecedores = Fornecedor.query.all()
    return render_template('devolucoes_compra/editar_devolucao_compra.html', devolucao=devolucao, produtos=produtos, fornecedores=fornecedores)

@app.route('/devolucoes_compra/excluir/<int:id>')
@login_required
def excluir_devolucao_compra(id):
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    devolucao = DevolucaoCompra.query.get_or_404(id)

    # Reverter estoque e saldo
    for item in devolucao.itens:
        item.produto.quantidade -= item.quantidade
    total_devolvido = sum(item.quantidade * item.produto.preco_compra for item in devolucao.itens)
    saldo = Saldo.query.first()
    if saldo:
        saldo.valor -= total_devolvido

    db.session.delete(devolucao)
    db.session.commit()
    flash('Devolução de compra excluída com sucesso!', 'success')
    return redirect(url_for('listar_devolucoes_compra'))

# ===================== GESTOR =====================
@app.route('/deposito', methods=['GET', 'POST'])
@login_required
def deposito():
    if current_user.tipo != 'Gestor':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        valor = float(request.form['valor'])
        saldo = Saldo.query.first()
        if not saldo:
            saldo = Saldo(valor=0.0)
            db.session.add(saldo)
        saldo.valor += valor
        db.session.commit()
        flash(f'Depósito de Kz {valor:.2f} realizado com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    saldo_atual = Saldo.query.first()
    saldo_valor = saldo_atual.valor if saldo_atual else 0.0
    return render_template('deposito.html', saldo=saldo_valor)

@app.route('/compras/excluir/<int:id>')
@login_required
def excluir_compra(id):
    # Gestores e Admins podem excluir compras
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    compra = Compra.query.get_or_404(id)
    db.session.delete(compra)
    db.session.commit()
    flash('Compra excluída com sucesso!', 'success')
    return redirect(url_for('listar_compras'))

# ===================== DEVOLUÇÕES =====================
@app.route('/devolucoes')
@login_required
def listar_devolucoes():
    if current_user.tipo not in ['Admin', 'Atendente']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    devolucoes = Devolucao.query.order_by(Devolucao.data.desc()).all()
    return render_template('devolucoes/listar_devolucoes.html', devolucoes=devolucoes)

@app.route('/devolucoes/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_devolucao():
    if current_user.tipo not in ['Admin', 'Atendente']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        import json
        itens = json.loads(request.form['itens'])
        motivo = request.form['motivo']
        venda_id = request.form.get('venda_id')
        if venda_id:
            venda_id = int(venda_id)

        nova_devolucao = Devolucao(motivo=motivo, venda_id=venda_id, usuario_id=current_user.id)
        db.session.add(nova_devolucao)
        db.session.flush()

        for item in itens:
            produto = Produto.query.get(item['id'])
            if produto:
                item_devolucao = ItemDevolucao(devolucao_id=nova_devolucao.id, produto_id=item['id'], quantidade=item['quantidade'])
                db.session.add(item_devolucao)
                # Atualizar estoque
                produto.quantidade += item['quantidade']

        db.session.commit()
        flash('Devolução adicionada com sucesso!', 'success')
        return redirect(url_for('listar_devolucoes'))
    produtos = Produto.query.all()
    vendas = Venda.query.all()
    return render_template('devolucoes/adicionar_devolucao.html', produtos=produtos, vendas=vendas, datetime=datetime)

@app.route('/devolucoes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_devolucao(id):
    if current_user.tipo != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    devolucao = Devolucao.query.get_or_404(id)
    if request.method == 'POST':
        import json
        itens = json.loads(request.form['itens'])
        motivo = request.form['motivo']
        venda_id = request.form.get('venda_id')
        if venda_id:
            venda_id = int(venda_id)

        # Deletar itens antigos
        ItemDevolucao.query.filter_by(devolucao_id=id).delete()

        # Atualizar devolução
        devolucao.motivo = motivo
        devolucao.venda_id = venda_id

        # Adicionar novos itens
        for item in itens:
            produto = Produto.query.get(item['id'])
            if produto:
                item_devolucao = ItemDevolucao(devolucao_id=devolucao.id, produto_id=item['id'], quantidade=item['quantidade'])
                db.session.add(item_devolucao)
                # Atualizar estoque
                produto.quantidade += item['quantidade']

        db.session.commit()
        flash('Devolução atualizada com sucesso!', 'success')
        return redirect(url_for('listar_devolucoes'))

    produtos = Produto.query.all()
    vendas = Venda.query.all()
    return render_template('devolucoes/editar_devolucao.html', devolucao=devolucao, produtos=produtos, vendas=vendas)

@app.route('/devolucoes/excluir/<int:id>')
@login_required
def excluir_devolucao(id):
    if current_user.tipo != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    devolucao = Devolucao.query.get_or_404(id)
    db.session.delete(devolucao)
    db.session.commit()
    flash('Devolução excluída com sucesso!', 'success')
    return redirect(url_for('listar_devolucoes'))

# ===================== RELATÓRIOS =====================
@app.route('/relatorios')
@login_required
def relatorios():
    if current_user.tipo not in ['Admin', 'Atendente', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta

    # Filtros de data
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    if not data_inicio:
        data_inicio = (datetime.now() - timedelta(days=30)).date().isoformat()
    if not data_fim:
        data_fim = datetime.now().date().isoformat()

    data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d').date()

    # Vendas (saídas) no período
    vendas = Venda.query.filter(func.date(Venda.data).between(data_inicio_dt, data_fim_dt)).order_by(Venda.data.desc()).all()
    total_vendas = sum(venda.total for venda in vendas)

    # Compras (entradas) no período
    compras = Compra.query.filter(func.date(Compra.data).between(data_inicio_dt, data_fim_dt)).order_by(Compra.data.desc()).all()
    total_compras = sum(compra.total for compra in compras)

    # Devoluções no período
    devolucoes = Devolucao.query.filter(func.date(Devolucao.data).between(data_inicio_dt, data_fim_dt)).order_by(Devolucao.data.desc()).all()
    devolucoes_com_totais = []
    for devolucao in devolucoes:
        total = sum(item.quantidade * Produto.query.get(item.produto_id).preco_venda for item in devolucao.itens)
        devolucoes_com_totais.append((devolucao, total))
    total_devolucoes = sum(total for _, total in devolucoes_com_totais)

    # Saldos
    saldo_entradas = total_vendas  # Vendas geram entrada de dinheiro
    saldo_saidas = total_compras + total_devolucoes  # Compras e devoluções geram saída de dinheiro
    saldo_liquido = saldo_entradas - saldo_saidas

    # Transações para histórico de saldo
    transacoes = []
    for venda in vendas:
        transacoes.append({'tipo': 'Venda', 'data': venda.data, 'valor': venda.total, 'saldo_acumulado': 0})
    for compra in compras:
        transacoes.append({'tipo': 'Compra', 'data': compra.data, 'valor': -compra.total, 'saldo_acumulado': 0})
    for devolucao, total in devolucoes_com_totais:
        transacoes.append({'tipo': 'Devolução', 'data': devolucao.data, 'valor': -total, 'saldo_acumulado': 0})

    # Ordenar por data
    transacoes.sort(key=lambda x: x['data'])

    # Calcular saldo acumulado
    saldo_atual = 0
    for transacao in transacoes:
        saldo_atual += transacao['valor']
        transacao['saldo_acumulado'] = saldo_atual

    # Detalhes das saídas
    saidas_detalhes = []
    for compra in compras:
        for item in compra.itens:
            saidas_detalhes.append({
                'tipo': 'Compra',
                'data': compra.data,
                'entidade': compra.fornecedor.nome,
                'produto': item.produto.nome,
                'quantidade': item.quantidade,
                'preco_unitario': item.preco_unitario,
                'subtotal': item.quantidade * item.preco_unitario
            })
    for devolucao, _ in devolucoes_com_totais:
        for item in devolucao.itens:
            preco_venda = Produto.query.get(item.produto_id).preco_venda
            saidas_detalhes.append({
                'tipo': 'Devolução',
                'data': devolucao.data,
                'entidade': devolucao.usuario.nome,
                'produto': item.produto.nome,
                'quantidade': item.quantidade,
                'preco_unitario': preco_venda,
                'subtotal': item.quantidade * preco_venda
            })

    # Ordenar saidas_detalhes por data
    saidas_detalhes.sort(key=lambda x: x['data'])

    # Vendas por mês (últimos 12 meses) - mantido para gráficos
    vendas_por_mes = db.session.query(
        extract('year', Venda.data).label('ano'),
        extract('month', Venda.data).label('mes'),
        func.sum(Venda.total).label('total')
    ).filter(Venda.data >= datetime.now() - timedelta(days=365)).group_by('ano', 'mes').order_by('ano', 'mes').all()

    # Produtos mais vendidos - mantido para gráficos
    produtos_mais_vendidos = db.session.query(
        Produto.nome,
        func.sum(ItemVenda.quantidade).label('total_vendido')
    ).join(ItemVenda).group_by(Produto.id).order_by(func.sum(ItemVenda.quantidade).desc()).limit(10).all()

    # Vendas por forma de pagamento - mantido para gráficos
    vendas_por_pagamento = db.session.query(
        Venda.forma_pagamento,
        func.count(Venda.id).label('quantidade'),
        func.sum(Venda.total).label('total')
    ).group_by(Venda.forma_pagamento).all()

    return render_template('relatorios.html',
                         vendas=vendas,
                         compras=compras,
                         devolucoes=devolucoes_com_totais,
                         total_vendas=total_vendas,
                         total_compras=total_compras,
                         total_devolucoes=total_devolucoes,
                         saldo_entradas=saldo_entradas,
                         saldo_saidas=saldo_saidas,
                         saldo_liquido=saldo_liquido,
                         transacoes=transacoes,
                         saidas_detalhes=saidas_detalhes,
                         data_inicio=data_inicio,
                         data_fim=data_fim,
                         vendas_por_mes=vendas_por_mes,
                         produtos_mais_vendidos=produtos_mais_vendidos,
                         vendas_por_pagamento=vendas_por_pagamento)

# ===================== CONFIGURAÇÕES =====================
@app.route('/configuracoes')
@login_required
def configuracoes():
    return render_template('configuracoes.html')

# ===================== ALERTAS DE VALIDADE =====================
@app.route('/alertas_validade')
@login_required
def alertas_validade():
    if current_user.tipo != 'Farmaceutica':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    
    hoje = datetime.now().date()
    daqui_30_dias = hoje + timedelta(days=30)
    
    # Produtos vencidos
    produtos_vencidos = Produto.query.filter(Produto.validade < hoje).all()
    
    # Produtos próximos a vencer (dentro de 30 dias)
    produtos_proximos_vencimento = Produto.query.filter(Produto.validade.between(hoje, daqui_30_dias)).all()
    
    return render_template('alertas_validade.html', 
                         produtos_vencidos=produtos_vencidos,
                         produtos_proximos_vencimento=produtos_proximos_vencimento)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5002)
