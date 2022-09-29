import random
random.seed(0)
import numpy as np
np.random.seed(0)
import tensorflow as tf
import onnx_graphsurgeon as gs
from utils.common_functions import (
    convert_axis,
    alternative_argmax,
)

def make_node(
    *,
    graph_node: gs.Node,
    tf_layers_dict: dict,
    **kwargs: dict,
):
    """ArgMax

    Parameters
    ----------
    graph_node: gs.Node
        graph_surgeon Node

    tf_layers_dict: dict
        optype, shape, dtype, tensorflow graph
    """
    graph_node_input: gs.Variable = graph_node.inputs[0]
    graph_node_output: gs.Variable = graph_node.outputs[0]
    shape = graph_node_output.shape
    dtype = graph_node_output.dtype

    replace_argmax_to_reducemax_and_indicies_is_int64 = \
        kwargs['replace_argmax_to_reducemax_and_indicies_is_int64']
    replace_argmax_to_reducemax_and_indicies_is_float32 = \
        kwargs['replace_argmax_to_reducemax_and_indicies_is_float32']

    axis = 0
    keepdims = True
    select_last_index = False

    if 'axis' in graph_node.attrs:
        axis = int(graph_node.attrs['axis'])
        # NCHW->NHWC, NCDHW->NDHWC
        axis = convert_axis(
            axis=axis,
            tensor_rank=len(shape),
        )

    if 'keepdims' in graph_node.attrs:
        # 0: False, 1: True
        keepdims = True if int(graph_node.attrs['keepdims']) == 1 else False

    if 'select_last_index' in graph_node.attrs:
        # 0: False, 1: True
        select_last_index = True if int(graph_node.attrs['select_last_index']) == 1 else False

    # Preserving Graph Structure (Dict)
    tf_layers_dict[graph_node_output.name] = {
        'optype': graph_node.op,
        'shape': shape,
        'dtype': dtype,
    }

    # Generation of TF OP
    ### 1. Select last index or first index
    reversed_tensor = None
    if not select_last_index:
        reversed_tensor = tf_layers_dict[graph_node_input.name]['tf_node']
    else:
        reversed_tensor = \
            tf.reverse(
                tensor=tf_layers_dict[graph_node_input.name]['tf_node'],
                axis=axis,
                name=f'{graph_node.name}_reverse',
            )

    ### 2. Replace ArgMax with a ReduceMax or no replace
    final_tensor = None
    if not replace_argmax_to_reducemax_and_indicies_is_int64 \
        and not replace_argmax_to_reducemax_and_indicies_is_float32:
        argmaxed_tensor = tf.math.argmax(
            input=reversed_tensor,
            axis=axis,
            output_type=dtype,
            name=f'{graph_node.name}_argmax',
        )
        if keepdims:
            final_tensor = \
                tf.expand_dims(
                    input=argmaxed_tensor,
                    axis=axis,
                    name=f'{graph_node.name}_expand_dims',
                )
        else:
            final_tensor = argmaxed_tensor
    else:
        final_tensor = alternative_argmax(
            input_tensor=reversed_tensor,
            axis=axis,
            output_type=tf.float32,
            keepdims=keepdims,
            replace_argmax_to_reducemax_and_indicies_is_int64=replace_argmax_to_reducemax_and_indicies_is_int64,
            replace_argmax_to_reducemax_and_indicies_is_float32=replace_argmax_to_reducemax_and_indicies_is_float32,
        )

    tf_layers_dict[graph_node_output.name]['tf_node'] = final_tensor