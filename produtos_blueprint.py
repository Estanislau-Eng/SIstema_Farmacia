from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Produto, Fornecedor
from datetime import datetime
from flask_login import current_user

produtos_bp = Blueprint('produtos_bp', __name__, template_folder='templates/produtos')

@produtos_bp.route('/')
def listar_produtos():
    produtos = Produto.query.all()
    return render_template('listar_produtos.html', produtos=produtos)

@produtos_bp.route('/adicionar', methods=['GET', 'POST'])
def adicionar_produto():
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('produtos_bp.listar_produtos'))
    if request.method == 'POST':
        produto = Produto(
            nome=request.form['nome'],
            categoria=request.form['categoria'],
            preco_compra=float(request.form['preco_compra']),
            preco_venda=float(request.form['preco_venda']),
            quantidade=int(request.form['quantidade']),
            validade=datetime.strptime(request.form['validade'], '%Y-%m-%d').date(),
            fornecedor_id=int(request.form['fornecedor_id']),
            data_compra=datetime.strptime(request.form['data_compra'], '%Y-%m-%d').date()
        )
        db.session.add(produto)
        db.session.commit()
        return redirect(url_for('produtos_bp.listar_produtos'))
    fornecedores = Fornecedor.query.all()
    return render_template('adicionar_produto.html', fornecedores=fornecedores, datetime=datetime)

@produtos_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    if current_user.tipo != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('produtos_bp.listar_produtos'))
    produto = Produto.query.get_or_404(id)
    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.categoria = request.form['categoria']
        produto.preco_compra = float(request.form['preco_compra'])
        produto.preco_venda = float(request.form['preco_venda'])
        produto.quantidade = int(request.form['quantidade'])
        produto.validade = datetime.strptime(request.form['validade'], '%Y-%m-%d').date()
        produto.fornecedor_id = int(request.form['fornecedor_id'])
        produto.data_compra = datetime.strptime(request.form['data_compra'], '%Y-%m-%d').date()
        db.session.commit()
        return redirect(url_for('produtos_bp.listar_produtos'))
    fornecedores = Fornecedor.query.all()
    return render_template('editar_produto.html', produto=produto, fornecedores=fornecedores)

@produtos_bp.route('/excluir/<int:id>')
def excluir_produto(id):
    if current_user.tipo not in ['Admin', 'Gestor']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('produtos_bp.listar_produtos'))
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    return redirect(url_for('produtos_bp.listar_produtos'))