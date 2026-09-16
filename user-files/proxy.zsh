# Managed helper definitions; runtime settings stay private and are never sourced.
typeset -g _WORKSTATION_PROXY_READER="${${(%):-%x}:A:h}/proxy-settings.py"

proxyon() {
  emulate -L zsh
  local _ws_data _ws_key _ws_index _ws_value
  local -a _ws_values _ws_keys
  _ws_keys=(http_proxy https_proxy all_proxy no_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY)
  for _ws_key in "${_ws_keys[@]}"; do
    if [[ ${parameters[$_ws_key]-} == *readonly* || ${parameters[$_ws_key]-} != scalar* && -v $_ws_key ]]; then
      print -u2 'Proxy variables must be writable scalars.'
      return 1
    fi
  done
  _ws_data=$(/usr/bin/python3 -B "$_WORKSTATION_PROXY_READER" "${WORKSTATION_PROXY_SETTINGS:-$HOME/.config/linux-os-setup/proxy.local.json}") || return 1
  _ws_values=("${(@0)_ws_data}")
  [[ ${#_ws_values} == 5 && $_ws_values[5] == OK ]] || return 1
  if [[ ${_WORKSTATION_PROXY_ACTIVE:-0} != 1 ]]; then
    typeset -gA _WORKSTATION_PROXY_VALUES=() _WORKSTATION_PROXY_TYPES=()
    for _ws_key in "${_ws_keys[@]}"; do
      _WORKSTATION_PROXY_TYPES[$_ws_key]=${parameters[$_ws_key]-unset}
      _WORKSTATION_PROXY_VALUES[$_ws_key]=${(P)_ws_key}
    done
    typeset -g _WORKSTATION_PROXY_ACTIVE=1
  fi
  for _ws_index in {1..8}; do
    _ws_key=$_ws_keys[$_ws_index]
    _ws_value=$_ws_values[$(( (_ws_index - 1) % 4 + 1 ))]
    typeset -gx "$_ws_key=$_ws_value"
  done
}

proxyoff() {
  emulate -L zsh
  [[ ${_WORKSTATION_PROXY_ACTIVE:-0} == 1 ]] || return 0
  local _ws_key
  for _ws_key in ${(k)_WORKSTATION_PROXY_TYPES}; do
    if [[ ${parameters[$_ws_key]-} == *readonly* || ${parameters[$_ws_key]-} != scalar* && -v $_ws_key ]]; then
      print -u2 'Proxy variables must be writable scalars before restoration.'
      return 1
    fi
  done
  for _ws_key in ${(k)_WORKSTATION_PROXY_TYPES}; do
    if [[ $_WORKSTATION_PROXY_TYPES[$_ws_key] == unset ]]; then
      unset "$_ws_key"
    else
      typeset -g "$_ws_key=$_WORKSTATION_PROXY_VALUES[$_ws_key]"
      if [[ $_WORKSTATION_PROXY_TYPES[$_ws_key] == *export* ]]; then
        typeset -gx "$_ws_key"
      else
        typeset -g +x "$_ws_key"
      fi
    fi
  done
  unset _WORKSTATION_PROXY_ACTIVE _WORKSTATION_PROXY_VALUES _WORKSTATION_PROXY_TYPES
}
