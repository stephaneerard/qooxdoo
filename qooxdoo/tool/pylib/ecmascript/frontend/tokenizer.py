#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################################
#
#  qooxdoo - the new era of web development
#
#  http://qooxdoo.org
#
#  Copyright:
#    2006-2010 1&1 Internet AG, Germany, http://www.1und1.de
#
#  License:
#    LGPL: http://www.gnu.org/licenses/lgpl.html
#    EPL: http://www.eclipse.org/org/documents/epl-v10.php
#    See the LICENSE file in the project's top-level directory for details.
#
#  Authors:
#    * Thomas Herchenroeder (thron7)
#
################################################################################

##
# This module implements a high-level scanner. It uses the low-level scanner
# from the Scanner module. The main additional functionality is to accumulate
# literals, such as strings, comments and regular expression literals, and to
# turn all tokens into dicts suitable for the consumption of the treegenerator
# parser module.
##

import sys, re
from ecmascript.frontend                 import lang, comment
from ecmascript.frontend.SyntaxException import SyntaxException
import Scanner

##
# Generator to turn low-level token tuples into Scanner.Token objects and
# provide and eof Token.
def tokens_2_obj(content):
    scanner = Scanner.Scanner(content)
    Token   = Scanner.Token
    for stoken in scanner:
        token = Token(stoken)
        yield token
    yield Token(('eof', '', token.spos+token.len, 0))


def scanner_slice(self, a, b):
    return self.content[a:b]


##
# Interface function
def parseStream(content, uniqueId=""):
    tokens = []
    line = column = sol = 1
    scanner = Scanner.LQueue(tokens_2_obj(content, ))
    scanner.content = content
    scanner.slice = scanner_slice
    for tok in scanner:
        # some inital values (tok isinstanceof Scanner.Token())
        token = {
            "source" : tok.value, 
            "detail" : "",
            "line"   : line, 
            "column" : tok.spos - sol + 1, 
            "id"     : uniqueId
            }

        # white space
        if (tok.name == 'white'):
            continue

        # end of file
        elif tok.name == 'eof':
            token['type'] = 'eof'
        
        # line break
        elif tok.name == 'nl':
            token['type']   = 'eol'
            token['source'] = ''    # that's the way the old tokenizer does it
            line += 1                  # increase line count
            sol  = tok.spos + tok.len  # char pos of next line start
        
        # float
        elif tok.name == 'float':
            token['type'] = 'number'
            token['detail'] = 'float'
        
        # hex integer
        elif tok.name == 'hexnum':
            token['type'] = 'number'
            token['detail'] = 'int'
        
        # integer
        elif tok.name == 'number':
            token['type'] = 'number'
            token['detail'] = 'int'
        
        # string
        elif tok.value in ('"', "'"):
            # accumulate strings
            token['type'] = 'string'
            if tok.value == '"':
                token['detail'] = 'doublequotes'
            else:
                token['detail'] = 'singlequotes'
            try:
                token['source'] = parseString(scanner, tok.value)
            except SyntaxException, e:
                desc = e.args[0] + " starting with %r..." % (tok.value + e.args[1])[:20]
                raiseSyntaxException(token, desc)
            token['source'] = token['source'][:-1]
            # adapt line number -- this assumes multi-line strings are not generally out
            linecnt = len(re.findall("\n", token['source']))
            if linecnt > 0:
                line += linecnt

        # identifier, operator
        elif tok.name in ("ident", "op", "mulop"):

            # JS operator symbols
            if tok.value in lang.TOKENS:
                # division, div-assignment, regexp
                if tok.value in ('/', '/='):
                    # accumulate regex literals
                    if (len(tokens) == 0 or (
                            (tokens[-1]['type']   != 'number') and
                            (tokens[-1]['detail'] != 'RP')     and
                            (tokens[-1]['detail'] != 'RB')     and
                            (tokens[-1]['type']   != 'name'))):
                        regexp = parseRegexp(scanner)
                        token['type'] = 'regexp'
                        token['source'] = tok.value + regexp
                    else:
                        token['type'] = 'token'
                        token['detail'] = lang.TOKENS[tok.value]

                # comment, inline
                elif tok.value == '//':
                    # accumulate inline comments
                    if (len(tokens) == 0 or
                        not is_last_escaped_token(tokens)):
                        commnt = parseCommentI(scanner)
                        token['type'] = 'comment'
                        token['source'] = tok.value + commnt
                        token['begin'] = not hasLeadingContent(tokens)
                        token['end'] = True
                        token['connection'] = "before" if token['begin'] else "after"  # "^//...\n i=1;" => comment *before* code; "i=1; //..." => comment *after* code
                        token['multiline'] = False
                        token['detail'] = 'inline'
                    else:
                        print >> sys.stderror, "Inline comment out of context"
                
                # comment, multiline
                elif tok.value == '/*':
                    # accumulate multiline comments
                    if (len(tokens) == 0 or
                        not is_last_escaped_token(tokens)):
                        token['type'] = 'comment'
                        try:
                            commnt = parseCommentM(scanner)
                        except SyntaxException, e:
                            desc = e.args[0] + " starting with \"%r...\"" % (tok.value + e.args[1])[:20]
                            raiseSyntaxException(token, desc)
                        token['source'] = tok.value + commnt
                        token['detail'] = comment.getFormat(token['source'])
                        token['begin'] = not hasLeadingContent(tokens)
                        if restLineIsEmpty(scanner):
                            token['end'] = True
                        else:
                            token['end'] = False
                        if token['begin']:
                            token['source'] = comment.outdent(token['source'], column - 1)
                        token['source'] = comment.correct(token['source'])
                        if token['end'] and not token['begin']:
                            token['connection'] = "after"
                        else:
                            token['connection'] = "before"
                        # adapt line number
                        linecnt = len(re.findall("\n", token['source']))
                        if linecnt > 0:
                            line += linecnt
                            token['multiline'] = True
                        else:
                            token['multiline'] = False

                    else:
                        print >> sys.stderror, "Multiline comment out of context"
                                
                # every other operator goes as is
                else:
                    token['type'] = 'token'
                    token['detail'] = lang.TOKENS[tok.value]
            
            # JS keywords
            elif tok.value in lang.RESERVED:
                token['type'] = 'reserved'
                token['detail'] = lang.RESERVED[tok.value]

            # JS/BOM objects
            elif tok.value in lang.BUILTIN:
                token['type'] = 'builtin'

            # identifier
            elif tok.value[:2] == "__":
                token['type'] = 'name'
                token['detail'] = 'private'
            elif tok.value[0] == "_":
                token['type'] = 'name'
                token['detail'] = 'protected'
            else:
                token['type'] = 'name'
                token['detail'] = 'public'

        # unknown token
        else:
            print >> sys.stderr, "Unhandled lexem: %s" % tok
            pass

        tokens.append(token)
    return tokens


##
# parse a string (both double and single quoted)
def parseString(scanner, sstart):
    # parse string literals
    result = []
    for token in scanner:
        result.append(token.value)
        if token.value == sstart:
            res = u"".join(result)
            if not Scanner.is_last_escaped(res):  # be aware of escaped quotes
                break
    else:
        # this means we've run out of tokens without finishing the string
        res = u"".join(result)
        raise SyntaxException("Non-terminated string", res)

    return res


def parseString1(scanner, sstart):
    # parse string literals
    tokens = parseDelimited(scanner, sstart)
    return scanner.slice(scanner, tokens[0].spos, tokens[-1].spos + tokens[-1].len)


##
# parse a regular expression
def parseRegexp(scanner):
    # leading '/' is already consumed
    rexp = ""
    token = scanner.next()
    while True:
        rexp += token.value      # accumulate token strings
        if rexp.endswith("/"):   # check for end of regexp
            # make sure "/" is not escaped, ie. preceded by an odd number of "\"
            if not Scanner.is_last_escaped(rexp):
                break
        token = scanner.next()

    # regexp modifiers
    try:
        if scanner.peek()[0].name == "ident":
            token = scanner.next()
            rexp += token.value
    except StopIteration:
        pass

    return rexp


def parseRegexp1(scanner):
    # leading '/' is already consumed
    tokens = parseDelimited(scanner, '/')

    # regexp modifiers
    try:
        if scanner.peek()[0].name == "ident":
            token = scanner.next()
            tokens.append(token)
    except StopIteration:
        pass

    return scanner.slice(scanner, tokens[0].spos, tokens[-1].spos + tokens[-1].len)


##
# parse an inline comment // ...
def parseCommentI(scanner):
    result = ""
    for token in scanner:
        if token.name == 'nl':
            scanner.putBack(token)
            break
        result += token.value
    return result


def parseCommentI1(scanner):
    tokens = parseDelimited (scanner, '\n')  # TODO: assumes universal newline!
    return scanner.slice(scanner, tokens[0].spos, tokens[-1].spos + tokens[-1].len)


##
# parse a multiline comment /* ... */
def parseCommentM(scanner):
    result = []
    res    = u""
    for token in scanner:
        result.append(token.value)
        if token.value == '*/':
            res = u"".join(result)
            if not Scanner.is_last_escaped(res):
                break
    else:
        # this means we've run out of tokens without finishing the comment
        res = u"".join(result)
        raise SyntaxException("Run-away comment", res)

    return res

def parseCommentM1(scanner):
    tokens = parseDelimited(scanner, '*/')
    return scanner.slice(scanner, tokens[0].spos, tokens[-1].spos + tokens[-1].len)


##
# generic element parser for delimited strings (string/regex literals, 
# comments)
# both start token and terminator token will be part of the element
def parseDelimited(scanner, terminator):
    tokens = []
    for token in scanner:
        tokens.append(token)
        if token.value == terminator:
            if not is_last_escaped_tokobj (tokens):
                break
    else:
        res = scanner.slice(tokens[0].spos, token.spos + token.len)
        raise SyntaxException ("Run-away element", res)

    return tokens



##
# syntax exception helper
def raiseSyntaxException (token, desc = u""):
    msg = desc + " (%s:%d)" % (token['id'], token['line'])
    raise SyntaxException (msg)

##
# check if the preceding tokens contain an odd number of '\'
def is_last_escaped_token(tokens):
    cnt = 0
    i   = 1
    while True:
        if tokens[-i]['source'] == '\\':
            cnt += 1
            i -= 1
        else:
            break
    return cnt % 2 == 1


def is_last_escaped_tokobj(tokens):
    cnt = 0
    i   = 1
    while True:
        if tokens[-i].value == '\\':
            cnt += 1
            i -= 1
        else:
            break
    return cnt % 2 == 1


##
# check if the rest of the line is empty (only white)
def restLineIsEmpty(scanner):
    try:
        toks = scanner.peek(2)
    except StopIteration:
        return True   # TODO: this is a hack

    if (toks[0].name == 'nl' or
        (toks[0].name == 'white' and toks[1].name == 'nl')):
        return True
    else:
        return False


##
# check if there is a preceding token on this line
def hasLeadingContent(tokens):
    # tokens empty
    if not len(tokens):
        return False
    else:
        if tokens[-1]["type"] == "eol":
            return False
        else:
            return True


