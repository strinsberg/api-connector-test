{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (python-pkgs: [
      python-pkgs.ipython
      python-pkgs.pandas
      python-pkgs.requests
      python-pkgs.sqlalchemy
      python-pkgs.plotly
      python-pkgs.dash
      python-pkgs.packaging
    ]))
  ];
}
