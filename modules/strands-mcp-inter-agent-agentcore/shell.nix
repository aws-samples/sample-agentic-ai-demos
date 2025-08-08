{ pkgs ? import <nixos-unstable> {} }:

  pkgs.mkShell {
    buildInputs = [
      pkgs.uv
      pkgs.nodejs
    ];
  }

