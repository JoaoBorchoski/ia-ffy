# IA-FFY

Sistema de consulta inteligente de cargas com agente de IA especializado em logística.

## Sobre o projeto

O IA-FFY é uma API que utiliza inteligência artificial para consultar e analisar dados de cargas de forma natural. O sistema permite que usuários façam perguntas em linguagem natural sobre cargas, status de entregas, documentos e outras informações logísticas.

### Como funciona

-   **Agente de IA**: Utiliza GPT-4 para processar perguntas em linguagem natural
-   **Banco de dados**: PostgreSQL com tabelas de proprietários, ofertas de carga e documentos
-   **Memória contextual**: Mantém histórico de conversas por usuário usando Redis
-   **API REST**: Endpoints para consultas via IA e listagem direta de cargas

### Principais funcionalidades

-   Busca de cargas por código, documento ou chave
-   Consulta de status de cargas (disponível, em trânsito, entregue)
-   Análise de documentos fiscais (NFe, CTe)
-   Histórico de conversas por usuário
-   Listagem completa de cargas por proprietário

## Como rodar o projeto

### 1. Iniciar o Docker

```bash
docker-compose up -d
```

### 2. Criar as tabelas e migrações básicas

Execute os seguintes comandos SQL no banco de dados:

```sql
CREATE TABLE owners (
    id UUID PRIMARY KEY,
    documento VARCHAR(20) UNIQUE NOT NULL,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    telefone VARCHAR(20),
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE oferta_carga (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nome_empresa_remetente VARCHAR(255) NOT NULL,
    endereco_remetente VARCHAR(255) NOT NULL,
    cidade_remetente VARCHAR(100) NOT NULL,
    estado_remetente VARCHAR(2) NOT NULL,
    nome_empresa_destinatario VARCHAR(255) NOT NULL,
    endereco_destinatario VARCHAR(255) NOT NULL,
    cidade_destinatario VARCHAR(100) NOT NULL,
    estado_destinatario VARCHAR(2) NOT NULL,
    status VARCHAR(50) DEFAULT 'disponivel',
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    pedido_embarcador VARCHAR(255) NOT null,
    FOREIGN KEY (owner_id) REFERENCES owners(id)
);

CREATE TABLE carga_documento (
    id UUID PRIMARY KEY,
    oferta_carga_id UUID NOT NULL,
    numero VARCHAR(50) NOT NULL,
    chave VARCHAR(100) UNIQUE NOT NULL,
    serie VARCHAR(50),
    tipo_documento VARCHAR(50) NOT NULL,
    data_emissao DATE,
    FOREIGN KEY (oferta_carga_id) REFERENCES oferta_carga(id)
);

INSERT INTO owners (id, documento, nome, email, telefone) VALUES
    (gen_random_uuid(), '12345678901', 'Transportadora ABC', 'contato@abc.com', '11987654321'),
    (gen_random_uuid(), '09876543210', 'Logística XYZ', 'comercial@xyz.com', '21912345678'),
    (gen_random_uuid(), '11223344556', 'Cargas Rápida S.A.', 'cargasrapidas@email.com', '41998877665');

INSERT INTO oferta_carga (id, owner_id, codigo, nome_empresa_remetente, endereco_remetente, cidade_remetente, estado_remetente, nome_empresa_destinatario, endereco_destinatario, cidade_destinatario, estado_destinatario, status, pedido_embarcador) VALUES
    (gen_random_uuid(), (SELECT id FROM owners WHERE documento = '12345678901'), 'OFR-001', 'Empresa A', 'Rua das Flores, 100', 'São Paulo', 'SP', 'Comércio B', 'Av. Central, 50', 'Rio de Janeiro', 'RJ', 'disponivel', 'teste 1'),
    (gen_random_uuid(), (SELECT id FROM owners WHERE documento = '12345678901'), 'OFR-002', 'Indústria C', 'Rua do Bosque, 25', 'Curitiba', 'PR', 'Fábrica D', 'Estrada Velha, 300', 'Porto Alegre', 'RS', 'em_transito', 'teste 2'),
    (gen_random_uuid(), (SELECT id FROM owners WHERE documento = '09876543210'), 'OFR-003', 'Empresa E', 'Rua Principal, 1', 'Belo Horizonte', 'MG', 'Comércio F', 'Av. Brasil, 400', 'Brasília', 'DF', 'disponivel', 'teste 3'),
    (gen_random_uuid(), (SELECT id FROM owners WHERE documento = '09876543210'), 'OFR-004', 'Logística G', 'Av. da Paz, 75', 'Manaus', 'AM', 'Distribuidora H', 'Rua da Alegria, 12', 'Belém', 'PA', 'entregue', 'teste 4');

INSERT INTO carga_documento (id, oferta_carga_id, numero, chave, serie, tipo_documento, data_emissao) VALUES
    (gen_random_uuid(), (SELECT id FROM oferta_carga WHERE codigo = 'OFR-001'), '00123456', '552408012345678901234567890123456789012345678901234', '1', 'NFe', '2025-09-15'),
    (gen_random_uuid(), (SELECT id FROM oferta_carga WHERE codigo = 'OFR-001'), '00987654', '552408987654321098765432109876543210987654321098765', '2', 'CTe', '2025-09-15'),
    (gen_random_uuid(), (SELECT id FROM oferta_carga WHERE codigo = 'OFR-002'), '00445566', '552408112233445566778899001122334455667788990011223', '3', 'NFe', '2025-09-14'),
    (gen_random_uuid(), (SELECT id FROM oferta_carga WHERE codigo = 'OFR-004'), '00112233', '552408998877665544332211009988776655443322110099887', '1', 'NFe', '2025-09-12');
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Rodar o projeto

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

O projeto estará disponível em: http://localhost:8000
