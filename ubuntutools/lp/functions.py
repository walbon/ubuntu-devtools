import cookie
import urlopener as lp_urlopener

def isLPTeamMember(team):
    """ Checks if the user is a member of a certain team on Launchpad.

        We do this by opening the team page on Launchpad and checking if the
        text "You are not a member of this team" is present using the
        user's cookie file for authentication.

        If the user is a member of the team: return True.
        If the user is not a member of the team: return False.
    """

    # TODO: Check if launchpadlib may be a better way of doing this.

    # Prepare cookie.
    cookieFile = cookie.prepareLaunchpadCookie()
    # Prepare URL opener.
    urlopener = lp_urlopener.setupLaunchpadUrlOpener(cookieFile)

    # Try to open the Launchpad team page:
    try:
        lpTeamPage = urlopener.open("https://launchpad.net/~%s" % team).read()
    except urllib2.HTTPError, error:
        print >> sys.stderr, "Unable to connect to Launchpad. Received a %s." % error.code
        sys.exit(1)

    # Check if text is present in page.
    if ("You are not a member of this team") in lpTeamPage:
        return False

    return True
