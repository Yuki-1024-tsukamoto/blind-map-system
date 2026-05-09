from schemas import Edge, Node, Project


DUMMY_PROJECTS = [
    Project(
        project_id="demo",
        title="Museum Demo",
        facility_type="exhibition",
        status="ready",
    )
]


DUMMY_NODES = [
    Node(
        node_id="N001",
        name="入口",
        floor_id="F1",
        x=0.0,
        y=0.0,
        description_ja="入口です。前方に受付があり、右側に展示室への通路があります。",
        description_en="This is the entrance. The reception desk is ahead, and the exhibition corridor is on the right.",
    ),
    Node(
        node_id="N002",
        name="受付",
        floor_id="F1",
        x=1.0,
        y=0.0,
        description_ja="受付カウンターです。案内表示とパンフレットがあります。",
        description_en="This is the reception counter. There are information signs and brochures.",
    ),
    Node(
        node_id="N003",
        name="展示室入口",
        floor_id="F1",
        x=2.0,
        y=0.0,
        description_ja="展示室の入口です。左側に展示パネル、右側に順路案内があります。",
        description_en="This is the entrance to the exhibition room. There is an exhibit panel on the left and route guidance on the right.",
    ),
]


DUMMY_EDGES = [
    Edge(
        edge_id="E001",
        from_node_id="N001",
        to_node_id="N002",
        direction="forward",
    ),
    Edge(
        edge_id="E002",
        from_node_id="N002",
        to_node_id="N003",
        direction="forward",
    ),
]