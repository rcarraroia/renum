
import Typewriter from '../components/Typewriter'
import ThemeToggle from '../components/ThemeToggle'

const Index = () => {
  return (
    <div className="flex h-screen flex-col md:grid md:grid-cols-2 lg:grid-cols-[60%_40%]">
      {/* Coluna Esquerda - Logo + Texto Principal com Typewriter */}
      <div className="relative hidden flex-1 flex-col justify-center bg-blue-50 px-5 pt-8 dark:bg-gray-900 md:flex md:px-6 md:py-[22px] lg:px-8">
        <div className="flex flex-col">
          <div className="mb-8 flex items-center gap-3">
            <div className="h-9 w-9 rounded-2xl flex items-center justify-center"
                 style={{ backgroundColor: 'hsl(var(--renum-primary) / 0.1)' }}>
              <span className="font-semibold text-renum-primary">R</span>
            </div>
            <span className="font-semibold text-renum-fg dark:text-white">RENUM</span>
          </div>
          
          <div className="flex flex-col text-[32px] leading-[1.2] md:text-[40px]">
            <h1 className="font-semibold tracking-tight text-renum-primary dark:text-purple-300">
              <Typewriter 
                texts={[
                  'Orquestre suas equipes de agentes de IA com o Renum',
                  'Crie workflows inteligentes e automatizados',
                  'Integre agentes do Suna com orquestração avançada',
                  'Resultados em tempo real, com simplicidade e potência'
                ]} 
                speed={30}
                pause={2000}
              />
            </h1>
          </div>
        </div>
      </div>

      {/* Coluna Direita - Botões e Links */}
      <div className="relative flex grow flex-col items-center justify-between bg-white px-5 py-8 dark:bg-black dark:text-white sm:rounded-t-[30px] md:rounded-none md:px-6">
        {/* Header Mobile/Desktop */}
        <header className="w-full flex items-center justify-between md:hidden">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-2xl flex items-center justify-center"
                 style={{ backgroundColor: 'hsl(var(--renum-primary) / 0.1)' }}>
              <span className="font-semibold text-renum-primary">R</span>
            </div>
            <span className="font-semibold">RENUM</span>
          </div>
          <ThemeToggle />
        </header>

        {/* Theme Toggle para Desktop */}
        <div className="hidden md:flex w-full justify-end">
          <ThemeToggle />
        </div>

        {/* Conteúdo Mobile - Título + Typewriter (visível apenas em mobile) */}
        <div className="flex flex-1 w-full items-center justify-center md:hidden">
          <div className="text-center">
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-renum-primary dark:text-purple-300 mb-4">
              <Typewriter 
                texts={[
                  'Orquestre suas equipes de agentes de IA',
                  'Workflows inteligentes e automatizados',
                  'Integração avançada com agentes do Suna'
                ]} 
                speed={35}
                pause={1800}
              />
            </h1>
          </div>
        </div>

        {/* Botões de Ação */}
        <div className="flex flex-col w-full max-w-sm gap-3">
          <a className="btn btn-primary w-full text-center" href="/signup">
            Cadastre-se gratuitamente
          </a>
          <a className="btn btn-secondary w-full text-center" href="/login">
            Entrar
          </a>
        </div>

        {/* Footer com Links Legais */}
        <footer className="w-full text-center text-sm text-gray-500 dark:text-gray-400">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <a href="/termos" className="hover:underline hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
              Termos de Uso
            </a>
            <span className="hidden sm:inline">•</span>
            <a href="/privacidade" className="hover:underline hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
              Política de Privacidade
            </a>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default Index
