#!/usr/bin/perl -w
#
# script smb2www-2.cgi : provide web interface to access smb filesystem
# with Filesys::SmbClient and libsmclient.so
# Copyright 2001 A.Barbet alian@alianwebserver.com.  All rights reserved.
#
# $Revision: 1.4 $
# $Date: 2002/01/05 14:03:58 $
# $Author: alian $
#------------------------------------------------------------------------------

use Filesys::SmbClient;
use CGI qw/:standard :html3 :netscape escape unescape/;
use CGI::Carp qw/fatalsToBrowser/;
use strict;

# ------ Config --------------------------------------------------------------#
my $SN = $ENV{SCRIPT_NAME} || "smb2www-2.cgi";
my $mimetype     = "/etc/mime.types";
my $user         = "alian";
my $password     = "password";
my $workgroup    = "alian";                      # optional
my $maskFile     = 0666;                         # for upload file
my $maskDir      = 0755;                         # for created dir
my $css          = "http://saturne/smb2www.css"; # for fun
# ------ End config ----------------------------------------------------------#

my $smb = new Filesys::SmbClient(username  => $user,
					   password  => $password,
					   workgroup => $workgroup,
					   debug     => 10)
  || die "Can't connect:$!\n";

&main();

sub main
  {
    my $buffer;
    # browse a share or a dir
    if (param('browse')) 
	{ print browse(param('browse')); }
    # read a file
    elsif (param('readfile')) 
	{ print read_file(param('readfile')); }
    # put a file
    elsif (param('filename')) 
	{ print upload_file(param('filename'), param('dir')); }
    # create a dir
    elsif (param('directory'))
	{
	  my $dir = param('dir').'/'.param('directory');
	  $smb->mkdir($dir, $maskDir) ||
	    print header,"Can't create ", $dir, ":$!\n";
	  print browse(param('dir'));
	}
    # delete a file
    elsif (param('delete') || param('deleteDir'))
	{
	  print header;
	  my $dir;
	  foreach my $f (param('delete')) 
	    { 
		if (unescape($f)=~/^(.*)\/[^\/]*$/) { $dir = $1; }
		my $res = $smb->unlink(unescape($f));
		if ($res) { print unescape($f)," deleted<br>\n"; }
		else { print "Can't delete ",unescape($f),":$!<br>\n"; }
	    }
	  foreach my $f (param('deleteDir')) 
	    { 
		if (unescape($f)=~/^(.*)\/[^\/]*$/) { $dir = $1; }
		my $res = $smb->rmdir_recurse(unescape($f));
		if ($res) { print unescape($f)," deleted<br>\n"; }
		else { print "Can't delete ",unescape($f),":$!<br>\n"; }
	    }

	  print "<a href=\"$SN?browse=$dir\">Back to $dir</a>",
	    end_html;
	}
    # first form
    else
	{
	  if ($workgroup)
	    { print browse("smb://".$workgroup); }	
	  else 
	    { 
		print header,
	        start_html
		    ( -'title'  => 'smb2www2',
			-'author' => 'alian@alianwebserver.com',
			-'meta'   => {'keywords'  => 'smb',
					  -'copyright'=>'Copyright 2001 AlianWebServer'},
			-'style'  => {'src' => $css},
			-'dtd'    => '-//W3C//DTD HTML 4.0 Transitional//EN"'.
			' "http://www.w3.org/TR/REC-html40/loose.dtd')."\n";
		}
	  print h1("smb2www - the come back"),
		  start_form.
		  textfield(-name=>'browse')."(ex: <i>smb://my_smb_server</i> or
                                               <i>smb://my_workgroup</i>)<br>".
		  submit."\n".end_form;
	}
    print end_html,"\n";
  }

#------------------------------------------------------------------------------
# Method that browse content of $rep
#------------------------------------------------------------------------------
sub browse
  {
    my ($rep) = @_;
    my ($i,$j,$tf,@lf,@lr,@ls,@lm,$buffer, $style)=(0,0,0);
    chop($rep) if ($rep=~/\/$/);
    return undef if (!$rep);

    # Read directory
    my $D = $smb->opendir($rep) || die "Can't read $rep:$!\n";
    my @f = $smb->readdir_struct($D);
    $smb->close($D);
    # Sort file by name
    @f = sort { $a->[1] cmp $b->[1] } @f;

    # For each item ...
    foreach my $f (@f)
	{
	  # Reformat url for dir . and ..
	  # and build new url in $ref
	  my $ref;
	  if ($f->[1] eq ".") { $ref = $rep; }
	  elsif ($f->[1] eq "..") 
	    { if ($rep=~/(.*)\/[^\/]*$/) { $ref = $1; } }
	  elsif ($f->[0] == SMBC_SERVER) { $ref = "smb://".$f->[1];}
	  else { $ref = $rep.'/'.$f->[1]; }
	  my $refe = escape($ref);

	  # A directory
	  if ($f->[0] == SMBC_DIR) 
	    { 
		# modulo for css style
		if (++$i % 2) { $style = "style1"; }
		else { $style = "style2"; }
		my $z="<input type=\"checkbox\" name=\"deleteDir\" 
                          value=\"$refe\">";
		# dont show delete for . and ..
		if ($f->[1] eq '.' || $f->[1] eq '..') { $z=" "; }
		my $item = "<tr class=\"$style\">
  <td class=\"name\" colspan=\"3\">
      [Dir] <a class=\"dir\" href=\"$SN?browse=$refe\">". $f->[1]."</a>
  </td>
  <td>$z</td>
</tr>\n"; 
		push(@lr, $item);
	    }
	  # A file
	  elsif ($f->[0] == SMBC_FILE) 
	    { 
		# modulo for css style
		if (++$j % 2) { $style = "style1"; }
		else { $style = "style2"; }
		my @l = $smb->stat($ref);
		my $item = "<tr class=\"$style\">
  <td class=\"name\"><a class=\"file\" href=\"$SN?readfile=$refe\">".
    $f->[1]."</a></td>
  <td class=\"size\">".sizeOf($l[7])."</td>
  <td class=\"time\">".localtime($l[11])."</td>
  <td><input type=\"checkbox\" name=\"delete\" value=\"$refe\"></td>
</tr>\n";
		push(@lf, $item); $tf+=$l[7];
	    }
	  # a share
	  elsif ($f->[0] == SMBC_FILE_SHARE) 
	    { 
		# modulo for css style
		if (++$i % 2) { $style = "style1"; }
		else { $style = "style2"; }

		my $item = "<tr class=\"$style\">
  <td class=\"name\">[Share] <a class=\"name\" href=\"$SN?browse=$refe\">".
    $f->[1]."</a></td>
  <td class=\"comment\">".$f->[2]."</td>
</tr>";
		push(@ls, $item); 
	    }
	  # a server
	  elsif ($f->[0] == SMBC_SERVER) 
	    {push(@lm, "[Server] <a class=\"server\" href=\"$SN?browse=$refe\">".
		  $f->[1]."</a>"); }
	}

    #
    # Html format
    #
    $buffer .= join("<br>\n", @lm)."<br>\n" if ($#lm != -1);
    if ($#ls != -1)
	{ $buffer .= "<table class=\"share\">".join(" ", @ls)."</table><br>\n"; }
    $buffer.="<form onsubmit=\"return confirm('Confirm ?')\">
<table border=\"1\">";
    if ($#lr != -1)
	{ $buffer .= join(" ", @lr); }
    if ($#lf != -1) 
	{ $buffer.= join("\n", @lf); }

    $buffer.="<td>".$#lf." file(s)</td>
              <td>".sizeOf($tf)."</td><td></td>
              <td><input type=\"submit\" value=\"delete\">" 
	if ($#lf != -1 or $#lr != -1);

    $buffer.="</table></form>\n";
    if ($#ls == -1 && $#lm == -1 && $#f != -1) 
	{
	  $buffer.= "<ul><li>".start_multipart_form().
                "Put a file on $rep:<br>".
                filefield(-name=>'filename',-size=>45).
		    hidden(-name=>'dir',-value=>$rep).
                submit('download','Upload').
		    endform."</li>\n<li>".
		    start_multipart_form().
                "Create a dir on $rep:<br>".
                textfield(-name=>'directory',-size=>45).
		    hidden(-name=>'dir',-value=>$rep).
                submit('download','Create').
		    endform."</li></ul>";
	}
    $buffer = header.
	        start_html
		    ( -'title'  => 'smb2www2',
			-'author' => 'alian@alianwebserver.com',
			-'meta'   => {'keywords'  => 'smb',
					  -'copyright'=>'Copyright 2001 AlianWebServer'},
			-'style'  => {'src' => $css},
			-'dtd'    => '-//W3C//DTD HTML 4.0 Transitional//EN"'.
			' "http://www.w3.org/TR/REC-html40/loose.dtd')."\n".
		 h1("You are on: ".linksOf(unescape($rep))).$buffer;
    return $buffer;
  }

#------------------------------------------------------------------------------
# Method that display file $file
#------------------------------------------------------------------------------
sub read_file
  {
    my ($file)=@_;
    my ($buffer, $ext);
    my $FD = $smb->open($file, 0666) || die "Can't read $file:$!\n";
    while (my $buf = $smb->read($FD, 1024)) { $buffer.=$buf; }
    $smb->close($FD);
    if (param('readfile')=~/\.(\w{0,5})$/) { $ext = $1; }
    return "Content-type: ".mimetype($ext, $mimetype)."\n\n".$buffer;
  }

#------------------------------------------------------------------------------
# Method that put a file push with http on directory $dir
#------------------------------------------------------------------------------
sub upload_file
  {
    my ($file, $dir)= @_;
    my($nom);
    if ($file=~/.*\\(.*)$/) {$nom=$1;}
    else {$nom=$file;}
    $nom = $dir."/".$file;
    my $FD = $smb->open(">$nom", 0666) || die "Can't create $nom:$!\n";
    while (<$file>) { $smb->write($FD, $_); }
    $smb->close($FD);
    return browse($dir);
  }

#------------------------------------------------------------------------------
# Determine mimetype, given a file extension
#------------------------------------------------------------------------------
sub mimetype 
  {
    my $test = lc $_[0];
    my $file = $_[1];
    my $type;
    open (MIME, $file) || die "can't read $file:$!\n";
  RULE: while ( <MIME> ) {
	my $line = $_;
	if ( not ($line =~ /^$/) and not ($line =~ /^\#/) ) 
	  {
	    if ( $line =~ /^([^\s]+)\s+([\w\ ]+)/ ) 
		{
		  $type = $1;
		  if ( $2 =~ /$test/ ) { last RULE; } 
		  else { $type = ""; }
		}
	  }
    }
    close MIME;
    $type = "application/octet-stream" if ($type eq "");
    return $type; 
  }

#------------------------------------------------------------------------------
# For a given url, split for each / and create a links for each parts
#------------------------------------------------------------------------------
sub linksOf
  {
    my ($url)=@_;
    my ($v,$u)=("smb://");
    if ($url =~ /^smb:\/\/(.+)/) 
	{
	  my $l=$1;
	  if ($l=~/\//)
	    {
		my @l = split(/\//,$l);
		foreach my $part (@l)
		  {
		    $v.=$part."/";
		    $u.="<a href=\"$SN?browse=$v\">$part</a>/";
		  }
	    }
	  else { $u = "<a href=\"$SN?browse=smb://$l\">$l</a>/"; }
	}
    if ($workgroup) 
	{$u = "<a href=\"$SN?browse=smb://$workgroup\">smb://</a>".$u; }
    else { $u = "smb://".$u; }
    return $u;
  }


#------------------------------------------------------------------------------
# For a size in octets, return a size in o. ko. mo. go
#------------------------------------------------------------------------------
sub sizeOf
  {
    my $size = shift;
    if ($size < 2**10) { return $size." o."; }
    elsif ($size < 2**20) { return sprintf("%.1f", $size/2**10)."Ko."; }
    elsif ($size < 2**30) { return sprintf("%.1f",$size/2**20)."Mo."; }
    elsif ($size < 2**40) { return sprintf("%.1f",$size/2**30)."Go."; }
  }