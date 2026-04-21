<br />
<div align="center">
  <a href="https://github.com/franciscoBSalgueiro/en-croissant">
    <img width="115" height="115" src="https://github.com/franciscoBSalgueiro/en-croissant/blob/master/src-tauri/icons/icon.png" alt="Logo">
  </a>

<h3 align="center">En Croissant</h3>

  <p align="center">
    The Ultimate Chess Toolkit
    <br />
    <a href="https://www.encroissant.org"><strong>encroissant.org</strong></a>
    <br />
    <br />
    <a href="https://discord.gg/tdYzfDbSSW">Discord Server</a>
    ·
    <a href="https://www.encroissant.org/download">Download</a>
    .
    <a href="https://www.encroissant.org/docs">Explore the docs</a>
  </p>
</div>

En-Croissant is an open-source, cross-platform chess GUI that aims to be powerful, customizable and easy to use.

## Features

- Store and analyze your games from [lichess.org](https://lichess.org) and [chess.com](https://chess.com)
- Multi-engine analysis. Supports all UCI engines
- Prepare a repertoire and train it with spaced repetition
- Simple engine and database installation and management
- Absolute or partial position search in the database

<img src="https://github.com/franciscoBSalgueiro/encroisssant-site/blob/master/public/showcase.webp" />

## Building from source

Refer to the [Tauri documentation](https://tauri.app/start/prerequisites/) for the requirements on your platform.

En-Croissant uses pnpm as the package manager for dependencies. Refer to the [pnpm install instructions](https://pnpm.io/installation) for how to install it on your platform.

### Windows Checklist

Install these tools first:

- Node.js
- `pnpm`
- Rust toolchain (`rustc`, `cargo`)
- Visual Studio Build Tools with `Desktop development with C++`

Useful checks:

```powershell
node -v
pnpm -v
rustc -V
cargo -V
```

If `pnpm` is missing:

```powershell
npm install -g pnpm
```

If Rust is missing, install it from:

- https://rustup.rs/

```bash
git clone https://github.com/franciscoBSalgueiro/en-croissant
cd en-croissant
pnpm install
pnpm dev
```

Use `pnpm dev` to run the desktop app directly from source with the current
frontend and Tauri/Rust logic.

If you want a rebuilt executable instead of a dev session:

```bash
pnpm build
```

The built app can be found at `src-tauri/target/release`

Important:

- Changing only a puzzle `.db3` does not change the behavior of a prebuilt app.
- If puzzle runtime logic changes in `src/` or `src-tauri/`, you must run the
  app from source (`pnpm dev`) or rebuild it (`pnpm build`) for those changes
  to take effect.

## Donate

If you wish to support the development of this GUI, you can do so [here](https://encroissant.org/support). All donations are greatly appreciated!

## Contributing

For contributing to this project please refer to the [Contributing guide](./CONTRIBUTING.md).

## License

This software is licensed under GPL-3.0 License.
