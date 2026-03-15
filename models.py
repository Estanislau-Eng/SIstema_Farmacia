from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Inicialização do SQLAlchemy
# Ajuste de schema para banco existente (usuarios: nome, usuario, senha, tipo)
db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    usuario = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # 'Admin', 'Atendente', 'Farmaceutica', 'Gestor'

    def __repr__(self):
        return f'<Usuario {self.nome} - {self.tipo}>'


class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(150), nullable=False)
    preco_compra = db.Column(db.Float, nullable=False)
    preco_venda = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    validade = db.Column(db.Date, nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=False)
    data_compra = db.Column(db.Date, nullable=False)
    fornecedor = db.relationship('Fornecedor', backref='produtos')

    def __repr__(self):
        return f'<Produto {self.nome} ({self.categoria})>'


class Fornecedor(db.Model):
    __tablename__ = 'fornecedores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    contato = db.Column(db.String(150), nullable=True)
    telefone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    endereco = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f'<Fornecedor {self.nome}>'


class Venda(db.Model):
    __tablename__ = 'vendas'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, nullable=False)
    forma_pagamento = db.Column(db.String(50), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario = db.relationship('Usuario', backref='vendas')

    def __repr__(self):
        return f'<Venda {self.id} - {self.total}>'


class ItemVenda(db.Model):
    __tablename__ = 'itens_venda'
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    venda = db.relationship('Venda', backref='itens')
    produto = db.relationship('Produto', backref='itens_venda')

    def __repr__(self):
        return f'<ItemVenda {self.produto.nome} x{self.quantidade}>'


class Compra(db.Model):
    __tablename__ = 'compras'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fornecedor = db.relationship('Fornecedor', backref='compras')
    usuario = db.relationship('Usuario', backref='compras')

    def __repr__(self):
        return f'<Compra {self.id} - {self.total}>'


class ItemCompra(db.Model):
    __tablename__ = 'itens_compra'
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compras.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    compra = db.relationship('Compra', backref='itens')
    produto = db.relationship('Produto', backref='itens_compra')

    def __repr__(self):
        return f'<ItemCompra {self.produto.nome} x{self.quantidade}>'


class Devolucao(db.Model):
    __tablename__ = 'devolucoes'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    motivo = db.Column(db.String(500), nullable=False)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'), nullable=True)  # Pode ser de uma venda ou não
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    venda = db.relationship('Venda', backref='devolucoes')
    usuario = db.relationship('Usuario', backref='devolucoes')

    def __repr__(self):
        return f'<Devolucao {self.id} - {self.motivo}>'


class ItemDevolucao(db.Model):
    __tablename__ = 'itens_devolucao'
    id = db.Column(db.Integer, primary_key=True)
    devolucao_id = db.Column(db.Integer, db.ForeignKey('devolucoes.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    devolucao = db.relationship('Devolucao', backref='itens')
    produto = db.relationship('Produto', backref='itens_devolucao')

    def __repr__(self):
        return f'<ItemDevolucao {self.produto.nome} x{self.quantidade}>'


class Saldo(db.Model):
    __tablename__ = 'saldo'
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f'<Saldo {self.valor}>'


class DevolucaoCompra(db.Model):
    __tablename__ = 'devolucoes_compra'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    motivo = db.Column(db.String(500), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fornecedor = db.relationship('Fornecedor', backref='devolucoes_compra')
    usuario = db.relationship('Usuario', backref='devolucoes_compra')

    def __repr__(self):
        return f'<DevolucaoCompra {self.id} - {self.motivo}>'


class ItemDevolucaoCompra(db.Model):
    __tablename__ = 'itens_devolucao_compra'
    id = db.Column(db.Integer, primary_key=True)
    devolucao_compra_id = db.Column(db.Integer, db.ForeignKey('devolucoes_compra.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    devolucao_compra = db.relationship('DevolucaoCompra', backref='itens')
    produto = db.relationship('Produto', backref='itens_devolucao_compra')

    def __repr__(self):
        return f'<ItemDevolucaoCompra {self.produto.nome} x{self.quantidade}>'