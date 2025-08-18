#!/usr/bin/env python3
"""
Script para executar a suíte completa de testes
Executa diferentes tipos de testes com configurações apropriadas
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, description):
    """Execute um comando e retorna o resultado"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Executando: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("✅ Sucesso!")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Falhou com código de saída {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Execute testes do sistema")
    parser.add_argument("--type", choices=["all", "unit", "integration", "performance", "security"], 
                       default="all", help="Tipo de testes para executar")
    parser.add_argument("--coverage", action="store_true", help="Gerar relatório de cobertura")
    parser.add_argument("--verbose", "-v", action="store_true", help="Saída verbosa")
    parser.add_argument("--fast", action="store_true", help="Pular testes lentos")
    parser.add_argument("--parallel", "-n", type=int, help="Número de workers paralelos")
    parser.add_argument("--file", help="Executar arquivo de teste específico")
    parser.add_argument("--function", help="Executar função de teste específica")
    
    args = parser.parse_args()
    
    # Configurar diretório de trabalho
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Verificar se pytest está instalado
    try:
        subprocess.run(["pytest", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pytest não encontrado. Instale com: pip install pytest")
        sys.exit(1)
    
    # Configurar comando base
    base_cmd = ["pytest"]
    
    # Adicionar opções baseadas nos argumentos
    if args.verbose:
        base_cmd.extend(["-v", "-s"])
    
    if args.coverage:
        base_cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term-missing"])
    
    if args.parallel:
        base_cmd.extend(["-n", str(args.parallel)])
    
    if args.fast:
        base_cmd.extend(["-m", "not slow"])
    
    # Executar testes baseados no tipo
    success = True
    
    if args.file:
        # Executar arquivo específico
        cmd = base_cmd + [f"tests/{args.file}"]
        if args.function:
            cmd.append(f"-k {args.function}")
        success = run_command(cmd, f"Executando {args.file}")
    
    elif args.type == "unit":
        cmd = base_cmd + ["-m", "unit", "tests/"]
        success = run_command(cmd, "Testes Unitários")
    
    elif args.type == "integration":
        cmd = base_cmd + ["-m", "integration", "tests/"]
        success = run_command(cmd, "Testes de Integração")
    
    elif args.type == "performance":
        cmd = base_cmd + ["-m", "performance", "tests/", "--durations=0"]
        success = run_command(cmd, "Testes de Performance")
    
    elif args.type == "security":
        cmd = base_cmd + ["-m", "security", "tests/"]
        success = run_command(cmd, "Testes de Segurança")
    
    elif args.type == "all":
        # Executar todos os tipos de teste em sequência
        test_suites = [
            (["pytest", "-m", "unit", "tests/"], "Testes Unitários"),
            (["pytest", "-m", "integration", "tests/"], "Testes de Integração"),
            (["pytest", "-m", "security", "tests/"], "Testes de Segurança"),
        ]
        
        # Adicionar testes de performance se não for modo rápido
        if not args.fast:
            test_suites.append((["pytest", "-m", "performance", "tests/", "--durations=0"], "Testes de Performance"))
        
        # Executar cada suíte
        for cmd_base, description in test_suites:
            cmd = cmd_base.copy()
            
            # Adicionar opções comuns
            if args.verbose:
                cmd.extend(["-v"])
            if args.parallel:
                cmd.extend(["-n", str(args.parallel)])
            
            if not run_command(cmd, description):
                success = False
                break
        
        # Executar com cobertura se solicitado
        if success and args.coverage:
            coverage_cmd = [
                "pytest", 
                "--cov=app", 
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing",
                "--cov-report=xml",
                "--cov-fail-under=80",
                "tests/"
            ]
            
            if args.fast:
                coverage_cmd.extend(["-m", "not slow"])
            
            run_command(coverage_cmd, "Relatório de Cobertura")
    
    # Executar verificações adicionais
    if success and args.type == "all":
        print(f"\n{'='*60}")
        print("🔍 Executando Verificações Adicionais")
        print(f"{'='*60}")
        
        # Verificar qualidade do código (se disponível)
        quality_checks = [
            (["python", "-m", "black", "--check", "app/"], "Verificação de Formatação (Black)"),
            (["python", "-m", "ruff", "check", "app/"], "Verificação de Lint (Ruff)"),
            (["python", "-m", "mypy", "app/"], "Verificação de Tipos (MyPy)"),
        ]
        
        for cmd, description in quality_checks:
            try:
                subprocess.run(cmd[0:2] + ["--version"], check=True, capture_output=True)
                run_command(cmd, description)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"⚠️  {description} - Ferramenta não encontrada, pulando...")
    
    # Resumo final
    print(f"\n{'='*60}")
    if success:
        print("✅ TODOS OS TESTES PASSARAM!")
        print("🎉 Sistema pronto para produção!")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        print("🔧 Verifique os erros acima e corrija antes de prosseguir.")
    print(f"{'='*60}")
    
    # Mostrar relatórios gerados
    if args.coverage:
        print("\n📊 Relatórios Gerados:")
        print("  - Cobertura HTML: htmlcov/index.html")
        print("  - Cobertura XML: coverage.xml")
    
    # Código de saída
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()