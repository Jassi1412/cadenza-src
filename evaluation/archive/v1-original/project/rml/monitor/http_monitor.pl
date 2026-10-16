:- use_module(library(http/thread_httpd)).
:- use_module(library(http/http_dispatch)).
:- use_module(library(http/http_client)).
:- use_module(library(http/json)).
:- use_module(library(http/json_convert)).
:- use_module(library(http/http_json)).

:- use_module(monitor(trace_expressions_semantics)).

:- http_handler(/,manage_request,[]).


%% Argomenti: specFile, [port], [logFile].
%% Se logFile dato, port e' obbligatorio (anche default).
%% Esempio: swipl -O -p monitor=PATH http_monitor.pl -- RMLspec.pl (port? | (port logFile)?)

% Inizializza stato worker: carica spec, imposta globale 'state'.

init :- current_prolog_flag(argv, Argv), Argv = [Spec|Rest], use_module(Spec), trace_expression(_, TE), nb_setval(state,TE),
(Rest = [Port|LogArg] -> atom_number(Port,Addr),nb_setval(port,Addr),(LogArg = [LogFile|_]->open(LogFile,append,Stream),nb_setval(log_file, Stream);nb_setval(log_file,null));nb_setval(port,80),nb_setval(log_file, null)).

:- thread_initialization(init).

%% Gestione file log opzionale.

:- if(nb_getval(log_file,null)).
log(_).
:- else.
log(Arg) :-
        nb_getval(log_file,Stream),
	(Arg=(TE1,E,TE2)->
	     writeln(Stream,"Initial state:"),writeln(Stream,TE1),writeln(Stream,"Event: "),writeln(Stream,E),writeln(Stream,"Final state:"),writeln(Stream,TE2);
	 writeln(Stream,"Logging error")),
	nl(Stream),
	flush_output(Stream).
:- endif.

server(Port) :- http_server(http_dispatch,[port(Port),workers(10)]).

manage_request(Request) :- 
    http_read_json_dict(Request, E),
    nb_getval(state,TE1),
    (next(TE1,E,TE2)->nb_setval(state,TE2),log((TE1,E,TE2)),reply_json_dict(_{error:false,event:E});log((TE1,E,error)),reply_json_dict(_{error:true,event:E})).

:- nb_getval(port,Port),initialization(server(Port)).
