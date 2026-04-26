import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      {/* Centered Hero Section */}
      <section id="center" className="container py-5">
        <div className="row justify-content-center align-items-center text-center">
          <div className="col-12 mb-4">
            <div className="d-flex flex-column align-items-center justify-content-center">
              <img src={heroImg} className="mb-3" width="170" height="179" alt="" />
              <div className="d-flex gap-3 justify-content-center">
                <img src={reactLogo} className="" alt="React logo" style={{width: 48}} />
                <img src={viteLogo} className="" alt="Vite logo" style={{width: 48}} />
              </div>
            </div>
          </div>
          <div className="col-12">
            <h1 className="display-5">Prompt Passthrough App</h1>
            <p className="lead">
              Edit <code>src/App.tsx</code> and save to test <code>HMR</code>
            </p>
            <button
              type="button"
              className="btn btn-primary btn-lg mt-3"
              onClick={() => setCount((count) => count + 1)}
            >
              Count is {count}
            </button>
          </div>
        </div>
      </section>

      {/* Next Steps Section */}
      <section id="next-steps" className="container py-5">
        <div className="row g-5">
          <div className="col-md-6">
            <div className="card h-100 shadow-sm">
              <div className="card-body text-center">
                <svg className="icon mb-2" role="presentation" aria-hidden="true">
                  <use href="/static/terminal_emulator/icons.svg#documentation-icon"></use>
                </svg>
                <h2 className="h4">Documentation</h2>
                <p>Your questions, answered</p>
                <ul className="list-unstyled">
                  <li className="mb-2">
                    <a href="https://vite.dev/" target="_blank" className="d-flex align-items-center gap-2 justify-content-center">
                      <img className="logo" src={viteLogo} alt="" style={{width: 24}} />
                      Explore Vite
                    </a>
                  </li>
                  <li>
                    <a href="https://react.dev/" target="_blank" className="d-flex align-items-center gap-2 justify-content-center">
                      <img className="button-icon" src={reactLogo} alt="" style={{width: 24}} />
                      Learn more
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div className="col-md-6">
            <div className="card h-100 shadow-sm">
              <div className="card-body text-center">
                <svg className="icon mb-2" role="presentation" aria-hidden="true">
                  <use href="/static/terminal_emulator/icons.svg#social-icon"></use>
                </svg>
                <h2 className="h4">Connect with us</h2>
                <p>Join the Vite community</p>
                <ul className="list-unstyled">
                  <li className="mb-2">
                    <a href="https://github.com/vitejs/vite" target="_blank" className="d-flex align-items-center gap-2 justify-content-center">
                      <svg className="button-icon" role="presentation" aria-hidden="true" style={{width: 24}}>
                        <use href="/static/terminal_emulator/icons.svg#github-icon"></use>
                      </svg>
                      GitHub
                    </a>
                  </li>
                  <li className="mb-2">
                    <a href="https://chat.vite.dev/" target="_blank" className="d-flex align-items-center gap-2 justify-content-center">
                      <svg className="button-icon" role="presentation" aria-hidden="true" style={{width: 24}}>
                        <use href="/static/terminal_emulator/icons.svg#discord-icon"></use>
                      </svg>
                      Discord
                    </a>
                  </li>
                  <li className="mb-2">
                    <a href="https://x.com/vite_js" target="_blank" className="d-flex align-items-center gap-2 justify-content-center">
                      <svg className="button-icon" role="presentation" aria-hidden="true" style={{width: 24}}>
                        <use href="/static/terminal_emulator/icons.svg#x-icon"></use>
                      </svg>
                      X.com
                    </a>
                  </li>
                  <li>
                    <a href="https://bsky.app/profile/vite.dev" target="_blank" className="d-flex align-items-center gap-2 justify-content-center">
                      <svg className="button-icon" role="presentation" aria-hidden="true" style={{width: 24}}>
                        <use href="/static/terminal_emulator/icons.svg#bluesky-icon"></use>
                      </svg>
                      Bluesky
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>
      {/* Spacer */}
      <div className="my-5"></div>
      <section id="spacer"></section>
    </>
  )
}

export default App
