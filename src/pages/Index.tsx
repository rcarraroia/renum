
import Typewriter from '../components/Typewriter'

const Index = () => {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between">
      <header className="w-full max-w-6xl px-6 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-2xl flex items-center justify-center"
               style={{ backgroundColor: 'hsl(var(--renum-primary) / 0.1)' }}>
            <span className="font-semibold" style={{ color: 'hsl(var(--renum-primary))' }}>R</span>
          </div>
          <span className="font-semibold">RENUM</span>
        </div>
        <nav className="flex items-center gap-3">
          <a className="btn btn-secondary" href="/login">Entrar</a>
          <a className="btn btn-primary" href="/signup">Cadastre-se</a>
        </nav>
      </header>

      <section className="flex flex-1 w-full items-center justify-center px-6">
        <div className="max-w-3xl text-center">
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-semibold tracking-tight">
            Orquestre suas equipes de agentes de IA com o Renum
          </h1>
          <p className="mt-5 text-lg" style={{ color: 'hsl(215.4 16.3% 46.9%)' }}>
            <Typewriter texts={[
              'Crie, execute e monitore workflows inteligentes.',
              'Integre agentes do Suna com orquestração avançada.',
              'Resultados em tempo real, com simplicidade e potência.',
            ]} />
          </p>
          <div className="mt-8 flex items-center justify-center gap-3 flex-col sm:flex-row">
            <a className="btn btn-primary" href="/signup">Começar gratuitamente</a>
            <a className="btn btn-secondary" href="/login">Já tenho conta</a>
          </div>
        </div>
      </section>

      <footer className="w-full max-w-6xl px-6 py-8 text-center text-sm" 
              style={{ color: 'hsl(215.4 16.3% 46.9%)' }}>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <a href="/termos" className="hover:underline">Termos de Uso</a>
          <span className="hidden sm:inline">•</span>
          <a href="/privacidade" className="hover:underline">Política de Privacidade</a>
        </div>
      </footer>
    </main>
  )
}

export default Index
