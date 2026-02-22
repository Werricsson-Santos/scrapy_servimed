#!/usr/bin/env python3
"""
Script para executar testes automatizados do projeto Scrapy Servimed
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description=""):
    """Executa comando e retorna resultado"""
    if description:
        print(f"\n🔄 {description}")
    
    print(f"Executando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr and result.returncode != 0:
        print(f"❌ Erro: {result.stderr}")
    
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description='Executa testes automatizados')
    parser.add_argument('--coverage', action='store_true', help='Gera relatório de cobertura')
    parser.add_argument('--verbose', '-v', action='store_true', help='Saída detalhada')
    parser.add_argument('--fast', action='store_true', help='Executa apenas testes unitários')
    parser.add_argument('--integration', action='store_true', help='Executa apenas testes de integração')
    parser.add_argument('--markers', type=str, help='Executa testes com marcadores específicos (ex: unit,celery)')
    
    args = parser.parse_args()
    
    # Verifica se está no diretório correto
    if not os.path.exists('servimed'):
        print("❌ Execute este script a partir da raiz do projeto (onde está o diretório servimed/)")
        sys.exit(1)
    
    # Comando base do pytest
    cmd = ['python', '-m', 'pytest']
    
    if args.verbose:
        cmd.extend(['-v', '-s'])
    
    if args.coverage:
        cmd.extend(['--cov=servimed', '--cov-report=html', '--cov-report=term-missing'])
    
    if args.fast:
        cmd.extend(['-m', 'unit'])
    elif args.integration:
        cmd.extend(['-m', 'integration'])
    elif args.markers:
        markers = args.markers.replace(',', ' or ')
        cmd.extend(['-m', markers])
    
    # Executa os testes
    print("🧪 Iniciando execução dos testes automatizados...")
    print("=" * 60)
    
    success = run_command(cmd, "Executando testes com pytest")
    
    if success:
        print("\n✅ Todos os testes foram executados com sucesso!")
        
        if args.coverage:
            print("\n📊 Relatório de cobertura gerado em htmlcov/index.html")
            print("Para visualizar, execute: python -m http.server 8000")
            print("E acesse: http://localhost:8000/htmlcov/")
    else:
        print("\n❌ Alguns testes falharam. Verifique a saída acima.")
        sys.exit(1)

if __name__ == '__main__':
    main()