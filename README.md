# infra2dot
Describe your IT infrastructure in plain text and convert it to a nice grah

![image](https://github.com/ndemou/infra2dot/assets/4411400/ea00083e-d46a-449e-b00c-62ed297e2b67)

# Quick Start

There are two steps. Create or edit a plain text file and run 2 commands to get the image. Specifically:

1. Create a plain text file where you describe your IT infrastructure and save it as `something.infra`. The above graph was created by this `.infra` file:

```
WebServices
    WebService_1  WebService_2
Databases
    Foo__MS_SQL
Clusters // Logical groups of IT Services
    GROUP
        SSO_SRV
        AADConnect
        WAF_AAG
    Microsoft
        M365
        Power_BI
        AzureAD
    Mimecast
        Mimecast
        Mimicast__SMTP
    ISP_1
Hosts // Which services are hosted by which device
    HQ_Router
        Open_Vpn__VPN
    Azure__Web1
        WebService_1
        WebService_2
    Azure__Server_3
        FooService
        Foo__MS_SQL
    HQ__DC
        Windows_AD__1
    HQ__Server_4
        File__Sharing
        Printer__Sharing
    Azure__Server_1 
        Lala_service
        Bar_service
    Azure__DC
        Windows_AD__2

Connections 
    Windows_AD__2 -- Windows_AD__1
    Windows_AD__1 --OpenVpn1-- SSO_SRV
    Windows_AD__1 --OpenVpn1-- AADConnect
    ISP_1 -- Open_Vpn__VPN
    /AAD/ -- AzureAD
    AADConnect -- /AAD/
    AzureAD -- M365
    AzureAD -- Power_BI
    Power_BI -- /SMTP/
    M365 -- /M365/
    WebService_2 -- WAF_AAG
    Bar_service -- Foo__MS_SQL
    Foo__MS_SQL -- FooService
    Foo__MS_SQL -- WebService_1
    FooService -- /SMTP/
    Lala_service -- /SMTP/
    WebService_1 -- /SMTP/
    WebService_1 -- WAF_AAG
    WAF_AAG-- /Internet/
    /SMTP/ -- Mimicast__SMTP
    /AAD/ -- Mimecast
    Mimecast -- /M365/
```

2. Run `infra2dot.py` like this to generate a .dot file and then an svg (or png etc):

    python infra2dot.py -f test.infra -t test-infra.dot
    dot -Tsvg test-infra.dot -o test-infra.svg

If you don't want to bother installing graphiz, copy/paste the output to some [graphiz online editor](https://www.google.com/search?q=online+graphiz+editor) like [this one](http://magjac.com/graphviz-visual-editor/) 

# Format of the input file (.infra)

`a  -- b` means that `a` is connected to `b` (e.g. application_service -- MS_SQL_server)

`a --foo-- b` means that `a` is connected to `b` via VPN `foo`

If you have a lot of complex connections you may get a mesh of lines that is
hard to follow. To connect two services a and b without a line from one to the 
other you can use this trick (inspired by the GND and VCC lines of electrical 
circuits):
    a -- /FOO/
    b -- /FOO/

# FAQ

## There are great free tools to draw such diagrams. What are the pros and cons of this method?

### Pros

You can create nice looking graphs very quickly. Especially if you need to create a lot of them. 

It's very easy to make small and/or incremental changes: Adding a new host and moving a service from another host to it, takes a few seconds. Same for deleting a host or moving a host from one group to another. In a GUI it may very well take half an hour if the objects you touch have central role in the diagram and you need to move a lot of stuff around them.

You do not waste your time twaking little details that don't matter.

You can generate `.infra` texts and hence nice diagrams programmatically.

### Cons

You can not create your first graph without investing(wasting?) a few minutes to understand the format of the text. 

You can not tweak little details that matter.

## Can I customize the colors or other details

There's no provision for this. It is very easy however to change the colors by changing the source code (search for `color`). You can change other details the same way if you a little bit of graphviz and its `.dot` language.
