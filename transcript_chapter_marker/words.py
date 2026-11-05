"""Stop words and text utilities for keyword extraction."""

STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are aren't as at be
    because been before being below between both but by can can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further had hadn't has hasn't have haven't having he he'd he'll he's
    her here here's hers herself him himself his how how's i i'd i'll i'm i've
    if in into is isn't it it's its itself let's me more most mustn't my myself
    no nor not of off on once only or other ought our ours ourselves out over
    own same shan't she she'd she'll she's should shouldn't so some such than
    that that's the their theirs them themselves then there there's these they
    they'd they'll they're they've this those through to too under until up very
    was wasn't we we'd we'll we're we've were weren't what what's when when's
    where where's which while who who's whom why why's with won't would wouldn't
    you you'd you'll you're you've your yours yourself yourselves
    just really okay ok like thing things stuff going gonna know mean means
    think say said says lot little bit come comes came got gets going want wanted
    one two three kind sort yeah yes yeah basically anyway anyways actually
    maybe something someone anything everything nothing everything's
    now right there here also even still well them's yeah's hey hello hi
    welcome thanks thank thanks' today talking talk episode video podcast
    transcript chapter recording start started started's let lets us
    um uh er ah hmm mhm huh oh ooh
    """.split()
)

KEPT_MIN_LEN = 3
